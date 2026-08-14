"""NoorBrain room-node audio service.

Run on a trusted Raspberry Pi with NOORBRAIN_NODE_TOKEN configured. Health is
read-only; microphone and speaker operations require the trust token.
"""

from __future__ import annotations

import base64
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException


app = FastAPI(title="NoorBrain Pi Audio Node", version="2.0.0")
NODE_ID = os.getenv("NOORBRAIN_NODE_ID", "room-pi").strip()
NODE_NAME = os.getenv("NOORBRAIN_NODE_NAME", "Room Pi").strip()
NODE_ROOM = os.getenv("NOORBRAIN_NODE_ROOM", "Unassigned").strip()
NODE_TOKEN = os.getenv("NOORBRAIN_NODE_TOKEN", "").strip()
STATE_LOCK = threading.RLock()
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


def set_volume(value: Any) -> bool:
    if value is None or not shutil.which("amixer"):
        return False
    volume = max(0, min(int(value), 100))
    subprocess.run(["amixer", "-q", "sset", "Master", f"{volume}%"], timeout=5, check=False)
    return True


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
    return True


def play_file(path: str, suffix: str) -> dict[str, Any]:
    global ACTIVE_PROCESS
    if suffix == ".wav":
        argv = [command("aplay"), "-q", path]
    else:
        argv = [command("ffplay"), "-nodisp", "-autoexit", "-loglevel", "quiet", path]
    stop_active()
    with STATE_LOCK:
        ACTIVE_PROCESS = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        process = ACTIVE_PROCESS
    try:
        _, stderr = process.communicate(timeout=180)
    except subprocess.TimeoutExpired as error:
        process.kill()
        raise HTTPException(504, "Playback timed out") from error
    finally:
        with STATE_LOCK:
            if ACTIVE_PROCESS is process:
                ACTIVE_PROCESS = None
    if process.returncode != 0:
        raise HTTPException(503, stderr.decode("utf-8", errors="replace")[-300:] or "Playback failed")
    return {"status": "played", "returncode": process.returncode}


@app.get("/health")
def health() -> dict[str, Any]:
    with STATE_LOCK:
        expired = [session_id for session_id, seen in LISTEN_SESSIONS.items() if time.time() - seen > 15]
        for session_id in expired:
            LISTEN_SESSIONS.pop(session_id, None)
        listening = bool(LISTEN_SESSIONS)
        playing = bool(ACTIVE_PROCESS and ACTIVE_PROCESS.poll() is None)
    return {
        "status": "healthy",
        "service": "noorbrain_pi_audio",
        "version": "2.0.0",
        "node_id": NODE_ID,
        "name": NODE_NAME,
        "room": NODE_ROOM,
        "trusted": bool(NODE_TOKEN),
        "capabilities": {
            "camera": False,
            "microphone": bool(shutil.which("arecord")),
            "speaker": bool(shutil.which("aplay") or shutil.which("ffplay")),
            "playback": bool(shutil.which("aplay") or shutil.which("ffplay")),
        },
        "remote_listening_active": listening,
        "playback_active": playing,
        "last_seen": time.time(),
    }


@app.post("/play")
def play(payload: dict = Body(...), x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    try:
        data = base64.b64decode(str(payload.get("audio_base64") or ""), validate=True)
    except Exception as error:
        raise HTTPException(422, "Invalid audio") from error
    if not data:
        raise HTTPException(422, "Audio is empty")
    fmt = str(payload.get("format") or "wav").lower()
    suffix = "." + (fmt if fmt in {"wav", "mp3", "ogg", "m4a", "aac", "webm", "opus"} else "wav")
    set_volume(payload.get("volume"))
    with tempfile.NamedTemporaryFile(suffix=suffix) as handle:
        handle.write(data)
        handle.flush()
        result = play_file(handle.name, suffix)
    return {**result, "bytes": len(data)}


@app.post("/tts")
def tts(payload: dict = Body(...), x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(422, "TTS text is required")
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    if not executable:
        raise HTTPException(503, "No TTS engine is installed on this node")
    set_volume(payload.get("volume"))
    stop_active()
    completed = subprocess.run([executable, text], capture_output=True, timeout=120, check=False)
    if completed.returncode != 0:
        raise HTTPException(503, completed.stderr.decode("utf-8", errors="replace")[-300:] or "TTS playback failed")
    return {"status": "played", "type": "tts", "characters": len(text)}


@app.post("/stop")
def stop(x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    return {"status": "stopped" if stop_active() else "idle"}


@app.post("/listen/start")
def listen_start(x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    command("arecord")
    session_id = secrets.token_urlsafe(24)
    with STATE_LOCK:
        LISTEN_SESSIONS[session_id] = time.time()
    return {"status": "listening", "session_id": session_id, "remote_listening_active": True}


@app.post("/listen/{session_id}/chunk")
def listen_chunk(session_id: str, payload: dict = Body(default={}), x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    with STATE_LOCK:
        if session_id not in LISTEN_SESSIONS:
            raise HTTPException(404, "Listening session not found")
        LISTEN_SESSIONS[session_id] = time.time()
    seconds = max(1, min(int(payload.get("seconds", 1)), 3))
    with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
        completed = subprocess.run(
            [command("arecord"), "-q", "-D", "default", "-f", "S16_LE", "-r", "16000", "-c", "1", "-d", str(seconds), handle.name],
            capture_output=True,
            timeout=seconds + 8,
            check=False,
        )
        if completed.returncode != 0:
            raise HTTPException(503, completed.stderr.decode("utf-8", errors="replace")[-300:] or "Microphone capture failed")
        audio = Path(handle.name).read_bytes()
    return {"status": "captured", "format": "wav", "seconds": seconds, "audio_base64": base64.b64encode(audio).decode("ascii"), "remote_listening_active": True}


@app.post("/listen/{session_id}/stop")
def listen_stop(session_id: str, x_noorbrain_node_token: str | None = Header(default=None)) -> dict[str, Any]:
    authorize(x_noorbrain_node_token)
    with STATE_LOCK:
        LISTEN_SESSIONS.pop(session_id, None)
    return {"status": "stopped", "remote_listening_active": False}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("NOORBRAIN_NODE_PORT", "8010")))
