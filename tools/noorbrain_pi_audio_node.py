"""Authoritative NoorBrain Raspberry Pi room-audio protocol.

Run with the NoorCameraNode virtual environment. Health is public; every
microphone, speaker, intercom, and control operation requires the shared node
token in X-NoorBrain-Node-Token.
"""

from __future__ import annotations

import base64
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException


VERSION = "2.1.0"
app = FastAPI(title="NoorBrain Pi Audio Node", version=VERSION)
NODE_ID = os.getenv("NOORBRAIN_NODE_ID", "existing-pi-audio").strip()
NODE_NAME = os.getenv("NOORBRAIN_NODE_NAME", "NoorBrain Raspberry Pi").strip()
NODE_ROOM = os.getenv("NOORBRAIN_NODE_ROOM", "Unassigned").strip()
NODE_TOKEN = os.getenv("NOORBRAIN_NODE_TOKEN", "").strip()
PLAYBACK_DEVICE = os.getenv("NOORBRAIN_PLAYBACK_DEVICE", "plughw:CARD=Headphones,DEV=0").strip()
CAPTURE_DEVICE = os.getenv("NOORBRAIN_CAPTURE_DEVICE", "plughw:CARD=Device,DEV=0").strip()
MAX_AUDIO_BYTES = max(1, int(os.getenv("NOORBRAIN_MAX_AUDIO_BYTES", str(32 * 1024 * 1024))))
STATE_LOCK = threading.RLock()
AUDIO_IO_LOCK = threading.RLock()
LISTEN_SESSIONS: dict[str, float] = {}
ACTIVE_PROCESS: subprocess.Popen[Any] | None = None


def command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise HTTPException(503, f"{name} is not installed on this node")
    return path


def authorize(x_noorbrain_node_token: str | None) -> None:
    if not NODE_TOKEN:
        raise HTTPException(503, "NOORBRAIN_NODE_TOKEN is not configured")
    if not x_noorbrain_node_token or not secrets.compare_digest(x_noorbrain_node_token, NODE_TOKEN):
        raise HTTPException(401, "Node authentication failed")


def _card_name(device: str) -> str:
    match = re.search(r"CARD=([^,]+)", device)
    return match.group(1) if match else ""


def hardware_available(executable: str, device: str) -> bool:
    if not shutil.which(executable):
        return False
    card = _card_name(device)
    if not card:
        return False
    try:
        cards = Path("/proc/asound/cards").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return card.lower() in cards.lower()


def set_volume(value: Any) -> bool:
    if value is None or not shutil.which("amixer"):
        return False
    volume = max(0, min(int(value), 100))
    card = _card_name(PLAYBACK_DEVICE)
    for control in ("Headphone", "Master"):
        completed = subprocess.run(
            ["amixer", "-q", "-D", f"hw:CARD={card}", "sset", control, f"{volume}%"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        if completed.returncode == 0:
            return True
    return False


def stop_active() -> bool:
    global ACTIVE_PROCESS
    with STATE_LOCK:
        process = ACTIVE_PROCESS
        ACTIVE_PROCESS = None
    if process is None or process.poll() is not None:
        return False
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    return True


def decode_audio(payload: dict[str, Any]) -> tuple[bytes, str]:
    try:
        audio = base64.b64decode(str(payload.get("audio_base64") or ""), validate=True)
    except Exception as error:
        raise HTTPException(422, "Invalid audio") from error
    if not audio:
        raise HTTPException(422, "Audio is empty")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio payload is too large")
    fmt = str(payload.get("format") or "wav").strip().lower()
    if fmt not in {"wav", "mp3", "ogg", "m4a", "aac", "webm", "opus"}:
        raise HTTPException(422, "Unsupported audio format")
    return audio, fmt


def _wav_for_playback(source: Path, fmt: str, directory: Path) -> Path:
    if fmt == "wav":
        return source
    output = directory / "decoded.wav"
    completed = subprocess.run(
        [command("ffmpeg"), "-nostdin", "-loglevel", "error", "-y", "-i", str(source), str(output)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or not output.is_file():
        raise HTTPException(422, completed.stderr.decode("utf-8", errors="replace")[-300:] or "Audio decoding failed")
    return output


def play_audio(payload: dict[str, Any], source_type: str) -> dict[str, Any]:
    global ACTIVE_PROCESS
    audio, fmt = decode_audio(payload)
    with AUDIO_IO_LOCK, tempfile.TemporaryDirectory(prefix="noorbrain-play-") as directory_name:
        stop_active()
        directory = Path(directory_name)
        source = directory / f"input.{fmt}"
        source.write_bytes(audio)
        playable = _wav_for_playback(source, fmt, directory)
        set_volume(payload.get("volume"))
        with STATE_LOCK:
            ACTIVE_PROCESS = subprocess.Popen(
                [command("aplay"), "-q", "-D", PLAYBACK_DEVICE, str(playable)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            process = ACTIVE_PROCESS
        try:
            _, stderr = process.communicate(timeout=180)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.wait(timeout=2)
            raise HTTPException(504, "Playback timed out") from error
        finally:
            with STATE_LOCK:
                if ACTIVE_PROCESS is process:
                    ACTIVE_PROCESS = None
        if process.returncode != 0:
            raise HTTPException(503, stderr.decode("utf-8", errors="replace")[-300:] or "Playback failed")
    return {
        "status": "played",
        "type": source_type,
        "bytes": len(audio),
        "format": fmt,
        "playback_device": PLAYBACK_DEVICE,
    }


def capture_audio(seconds: int) -> dict[str, Any]:
    duration = max(1, min(int(seconds), 15))
    with AUDIO_IO_LOCK, tempfile.TemporaryDirectory(prefix="noorbrain-record-") as directory:
        stop_active()
        output = Path(directory) / "capture.wav"
        completed = subprocess.run(
            [
                command("arecord"), "-q", "-D", CAPTURE_DEVICE,
                "-f", "S16_LE", "-r", "16000", "-c", "1",
                "-d", str(duration), str(output),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=duration + 8,
            check=False,
        )
        if completed.returncode != 0 or not output.is_file():
            raise HTTPException(503, completed.stderr.decode("utf-8", errors="replace")[-300:] or "Microphone capture failed")
        audio = output.read_bytes()
    return {
        "status": "captured",
        "format": "wav",
        "seconds": duration,
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "capture_device": CAPTURE_DEVICE,
    }


def expire_sessions() -> None:
    with STATE_LOCK:
        expired = [session_id for session_id, seen in LISTEN_SESSIONS.items() if time.time() - seen > 15]
        for session_id in expired:
            LISTEN_SESSIONS.pop(session_id, None)


@app.get("/health")
def health() -> dict[str, Any]:
    expire_sessions()
    speaker = hardware_available("aplay", PLAYBACK_DEVICE)
    microphone = hardware_available("arecord", CAPTURE_DEVICE)
    with STATE_LOCK:
        listening = bool(LISTEN_SESSIONS)
        playing = bool(ACTIVE_PROCESS and ACTIVE_PROCESS.poll() is None)
    return {
        "status": "healthy" if NODE_TOKEN and speaker and microphone else "degraded",
        "service": "noorbrain_pi_audio",
        "version": VERSION,
        "node_id": NODE_ID,
        "name": NODE_NAME,
        "room": NODE_ROOM,
        "trusted": bool(NODE_TOKEN),
        "speaker_available": speaker,
        "microphone_available": microphone,
        "playback_device": PLAYBACK_DEVICE,
        "capture_device": CAPTURE_DEVICE,
        "capabilities": {
            "camera": False,
            "microphone": microphone,
            "speaker": speaker,
            "playback": speaker,
        },
        "remote_listening_active": listening,
        "playback_active": playing,
        "last_seen": time.time(),
    }


@app.post("/play")
def play(payload: dict = Body(...), x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    return play_audio(payload, str(payload.get("source_type") or "audio"))


@app.post("/talk")
def talk(payload: dict = Body(...), x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    return play_audio(payload, "intercom")


@app.post("/stop")
def stop(x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    return {"status": "stopped" if stop_active() else "idle", "playback_active": False}


@app.post("/record")
def record(payload: dict = Body(default={}), x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    return capture_audio(payload.get("seconds", 4))


@app.post("/listen/start")
def listen_start(x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    if not hardware_available("arecord", CAPTURE_DEVICE):
        raise HTTPException(503, "Configured microphone is unavailable")
    session_id = secrets.token_urlsafe(24)
    with STATE_LOCK:
        LISTEN_SESSIONS[session_id] = time.time()
    return {"status": "listening", "session_id": session_id, "remote_listening_active": True}


@app.post("/listen/{session_id}/chunk")
def listen_chunk(
    session_id: str,
    payload: dict = Body(default={}),
    x_noorbrain_node_token: str | None = Header(default=None),
) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    expire_sessions()
    with STATE_LOCK:
        if session_id not in LISTEN_SESSIONS:
            raise HTTPException(404, "Listening session not found")
        LISTEN_SESSIONS[session_id] = time.time()
    return {**capture_audio(payload.get("seconds", 1)), "remote_listening_active": True}


@app.post("/listen/{session_id}/stop")
def listen_stop(session_id: str, x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    with STATE_LOCK:
        LISTEN_SESSIONS.pop(session_id, None)
    return {"status": "stopped", "remote_listening_active": False}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("NOORBRAIN_NODE_PORT", "8010")))
