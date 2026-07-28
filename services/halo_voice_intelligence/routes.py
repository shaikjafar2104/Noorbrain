from __future__ import annotations

import asyncio
import base64
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .pipeline import voice_intelligence_pipeline
from .stt_service import stt_service
from .vad_service import vad_service
from .wakeword_service import wakeword_service

router = APIRouter(
    prefix="/api/halo-voice-intelligence",
    tags=["HALO Voice Intelligence"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_voice_intelligence",
        "version": "3.1-c1.3-c1.5",
        "wakeword": wakeword_service.status(),
        "vad": vad_service.status(),
        "stt": stt_service.health(),
    }


@router.post("/wakeword/detect")
async def detect_wakeword(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    return wakeword_service.detect(str(payload.get("text") or ""))


@router.post("/wakeword/configure")
async def configure_wakeword(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return wakeword_service.configure(
            list(payload.get("wake_words") or [])
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/vad/analyze")
async def analyze_vad(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        audio = base64.b64decode(
            str(payload.get("audio_base64") or ""),
            validate=True,
        )
        return vad_service.analyze_pcm16(audio)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid audio payload: {exc}",
        ) from exc


@router.patch("/vad/config")
async def configure_vad(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return vad_service.configure(float(payload.get("threshold")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/stt/transcribe")
async def transcribe(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        audio = base64.b64decode(
            str(payload.get("audio_base64") or ""),
            validate=True,
        )
        return await asyncio.to_thread(
            stt_service.transcribe,
            audio,
            sample_rate=int(payload.get("sample_rate", 16000)),
            channels=int(payload.get("channels", 1)),
            backend=str(payload.get("backend", "auto")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid STT payload: {exc}",
        ) from exc


@router.post("/pipeline/text")
async def process_text(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    return voice_intelligence_pipeline.process_text(
        str(payload.get("text") or "")
    )


@router.post("/pipeline/audio")
async def process_audio(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        audio = base64.b64decode(
            str(payload.get("audio_base64") or ""),
            validate=True,
        )
        return await asyncio.to_thread(
            voice_intelligence_pipeline.process_audio,
            audio,
            sample_rate=int(payload.get("sample_rate", 16000)),
            channels=int(payload.get("channels", 1)),
            backend=str(payload.get("backend", "auto")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid pipeline payload: {exc}",
        ) from exc
