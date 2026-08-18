from __future__ import annotations

import asyncio
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/api/halo-voice", tags=["HALO Voice"])

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "halo_voice.json"
CACHE_DIR = ROOT / "data" / "voice_cache"
MODEL_DIR = CACHE_DIR / "models"

_model = None
_model_key = None
_model_lock = threading.Lock()
_model_loaded_at = None


def load_config() -> dict[str, Any]:
    cpu_count = max(1, os.cpu_count() or 2)
    config: dict[str, Any] = {
        "enabled": True,
        "model": os.getenv("NOORBRAIN_WHISPER_MODEL", "base"),
        "device": "cpu",
        "compute_type": "int8",
        "language": None,
        "wake_phrase": "halo",
        "require_wake_phrase": False,
        "minimum_audio_bytes": 900,
        "cpu_threads": min(cpu_count, 6),
        "num_workers": 1,
        "beam_size": 1,
    }
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            config.update(saved)
    except Exception:
        pass
    return config


def get_model():
    global _model, _model_key, _model_loaded_at

    config = load_config()
    key = (
        str(config["model"]),
        str(config["device"]),
        str(config["compute_type"]),
        int(config["cpu_threads"]),
        int(config["num_workers"]),
    )

    with _model_lock:
        if _model is not None and _model_key == key:
            return _model

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is missing from the NoorBrain virtual environment."
            ) from exc

        MODEL_DIR.mkdir(parents=True, exist_ok=True)

        _model = WhisperModel(
            key[0],
            device=key[1],
            compute_type=key[2],
            cpu_threads=key[3],
            num_workers=key[4],
            download_root=str(MODEL_DIR),
        )
        _model_key = key
        _model_loaded_at = time.time()
        return _model


def transcribe_file(path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    config = load_config()
    model = get_model()

    segments, info = model.transcribe(
        str(path),
        language=config.get("language") or None,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 220,
            "speech_pad_ms": 120,
        },
        beam_size=int(config.get("beam_size", 1)),
        best_of=1,
        temperature=0,
        condition_on_previous_text=False,
        without_timestamps=True,
    )

    text = " ".join(
        segment.text.strip()
        for segment in segments
        if segment.text and segment.text.strip()
    ).strip()

    wake_phrase = str(config.get("wake_phrase") or "halo").strip()
    wake_detected = text.lower().strip().startswith(wake_phrase.lower())
    command = text[len(wake_phrase):].lstrip(" ,:-") if wake_detected else text

    if config.get("require_wake_phrase") and not wake_detected:
        command = ""

    return {
        "text": text,
        "command": command,
        "wake_detected": wake_detected,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "model": config["model"],
        "transcription_ms": round((time.perf_counter() - started) * 1000),
    }


@router.get("/health")
async def health() -> dict[str, Any]:
    ready = True
    error = None
    try:
        import faster_whisper  # noqa: F401
    except Exception as exc:
        ready = False
        error = str(exc)

    config = load_config()
    return {
        "status": "healthy" if ready else "dependency_missing",
        "service": "halo_voice",
        "version": "3.1.0",
        "universal_gateway": True,
        "low_latency": True,
        "dependency_ready": ready,
        "dependency_error": error,
        "model": config["model"],
        "model_loaded": _model is not None,
        "cpu_threads": config["cpu_threads"],
        "beam_size": config["beam_size"],
    }


@router.post("/warmup")
async def warmup() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        await asyncio.to_thread(get_model)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "status": "ready",
        "model": load_config()["model"],
        "warmup_ms": round((time.perf_counter() - started) * 1000),
        "already_loaded": _model_loaded_at is not None,
    }


@router.get("/diagnostics")
async def diagnostics() -> dict[str, Any]:
    config = load_config()
    return {
        "status": "ok",
        "config": config,
        "model_loaded": _model is not None,
        "cache_path": str(CACHE_DIR),
    }


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict[str, Any]:
    config = load_config()
    if not config["enabled"]:
        raise HTTPException(status_code=503, detail="HALO Voice is disabled.")

    suffix = Path(audio.filename or "voice.webm").suffix or ".webm"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=suffix, dir=CACHE_DIR, delete=False) as handle:
        temp_path = Path(handle.name)
        total = 0
        while True:
            chunk = await audio.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            handle.write(chunk)

    try:
        if total < int(config.get("minimum_audio_bytes", 900)):
            raise HTTPException(
                status_code=422,
                detail="Recording too short. Speak for 2–4 seconds.",
            )

        result = await asyncio.to_thread(transcribe_file, temp_path)

        if not result["text"]:
            raise HTTPException(
                status_code=422,
                detail="No clear speech detected. Speak closer to the microphone.",
            )

        return {"status": "ok", "audio_bytes": total, **result}
    finally:
        temp_path.unlink(missing_ok=True)
