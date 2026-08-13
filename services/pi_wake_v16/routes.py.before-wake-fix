from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from threading import RLock
from typing import Any

from fastapi import APIRouter, Body, HTTPException


router = APIRouter(prefix="/api/pi-wake-v16", tags=["Pi HALO Wake Word"])
ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "data" / "pi_wake_v16.json"
LOCK = RLock()
DEFAULT = {
    "version": "16.1.0",
    "enabled": True,
    "wake_words": ["noor", "hey noor"],
    "armed_seconds": 8,
    "armed_until": 0.0,
    "last_event": None,
}


def read_state() -> dict[str, Any]:
    with LOCK:
        try:
            loaded = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            loaded = {}
        return {**DEFAULT, **(loaded if isinstance(loaded, dict) else {})}


def write_state(data: dict[str, Any]) -> None:
    with LOCK:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STATE.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temporary.replace(STATE)


def extract_command(text: str) -> tuple[bool, str]:
    clean = " ".join(text.strip().split())
    normalized = re.sub(r"[^a-z0-9']+", " ", clean.casefold()).strip()
    words = normalized.split()

    if not words:
        return False, ""

    if words[0] == "hey":
        words.pop(0)

    if not words:
        return False, ""

    wake_variants = {
        "noor", "nor", "nur", "no",
        "nour", "noore",
    }

    if words[0] not in wake_variants:
        return False, clean

    words.pop(0)

    if words and words[0] == "halo":
        words.pop(0)

    command = " ".join(words).strip()

    command = re.sub(
        r"^(?:what's|whats|what)\\s+(?:tham|tam|time)\\s+is\\s+it$",
        "what time is it",
        command,
    )

    return True, command

def natural_audio(text: str) -> dict[str, Any] | None:
    """Return Piper audio only. Never fall back to electronic espeak."""
    piper = shutil.which("piper") or str(ROOT / "tools" / "piper" / "piper")
    model = os.getenv("PIPER_MODEL_PATH", "").strip() or str(ROOT / "models" / "voice" / "en_US-lessac-medium.onnx")
    if not piper or not model or not Path(model).is_file() or not text.strip():
        return None
    with tempfile.NamedTemporaryFile(suffix=".wav") as output:
        completed = subprocess.run(
            [piper, "--model", model, "--output_file", output.name],
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=90,
            check=False,
        )
        if completed.returncode != 0:
            return None
        audio = Path(output.name).read_bytes()
    return {"format": "wav", "audio_base64": base64.b64encode(audio).decode("ascii")}


def process_audio(audio: bytes) -> dict[str, Any]:
    from services.halo_voice.routes import transcribe_file
    from services.voice_os.engine import voice_os_engine

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        path = Path(handle.name)
        handle.write(audio)
    try:
        transcript = transcribe_file(path)
    finally:
        path.unlink(missing_ok=True)

    text = str(transcript.get("text") or "").strip()
    wake, command = extract_command(text)
    state = read_state()
    now = time.time()
    armed = float(state.get("armed_until", 0)) > now

    if not wake and not armed:
        result = {"status": "ignored", "text": text, "reason": "Wake word not detected"}
    elif wake and not command:
        state["armed_until"] = now + int(state.get("armed_seconds", 8))
        result = {"status": "awake", "text": text, "command": "", "reply": "", "armed_seconds": state["armed_seconds"]}
    else:
        execution = voice_os_engine.process(
            command,
            session_id="raspberry-pi-halo",
            confirm=False,
            speak=False,
        )
        reply = str(execution.get("reply") or "").strip()
        state["armed_until"] = 0.0
        result = {
            "status": "handled" if execution.get("status") == "ok" else execution.get("status", "error"),
            "text": text,
            "command": command,
            "reply": reply,
            "intent": execution.get("intent"),
            "action": execution.get("action"),
            "response_audio": natural_audio(reply),
            "electronic_voice": False,
        }

    state["last_event"] = {**result, "response_audio": bool(result.get("response_audio")), "timestamp": now}
    write_state(state)
    return result


@router.get("/health")
async def health():
    state = read_state()
    return {
        "status": "healthy",
        "service": "pi_halo_wakeword",
        "version": "16.1.0",
        "wake_words": state["wake_words"],
        "armed": float(state.get("armed_until", 0)) > time.time(),
        "natural_voice_ready": bool(shutil.which("piper") and os.getenv("PIPER_MODEL_PATH")),
        "electronic_voice": False,
        "last_event": state.get("last_event"),
    }


@router.post("/process")
async def process(payload: dict[str, Any] = Body(...)):
    if not read_state().get("enabled", True):
        raise HTTPException(503, "Pi wake-word listener is disabled")
    try:
        audio = base64.b64decode(str(payload.get("audio_base64") or ""), validate=True)
    except Exception as error:
        raise HTTPException(422, "Invalid audio") from error
    if len(audio) < 1000:
        raise HTTPException(422, "Audio is too short")
    try:
        return await asyncio.to_thread(process_audio, audio)
    except Exception as error:
        raise HTTPException(500, f"{type(error).__name__}: {error}") from error


@router.patch("/config")
async def configure(payload: dict[str, Any] = Body(...)):
    state = read_state()
    if "enabled" in payload:
        state["enabled"] = bool(payload["enabled"])
    if "armed_seconds" in payload:
        state["armed_seconds"] = max(3, min(int(payload["armed_seconds"]), 30))
    write_state(state)
    return {"status": "updated", "config": state}
