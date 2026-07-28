from __future__ import annotations

import asyncio
import base64
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .device_config import voice_device_config
from .offline_stt import offline_stt
from .offline_tts import offline_tts
from .qa import voice_qa

router = APIRouter(prefix="/api/voice-os/qa4", tags=["Voice OS Pack 4"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "voice_os_pack4",
        "version": "3.0-phaseB-pack4",
        "stt": offline_stt.health(),
        "tts": offline_tts.health(),
        "config": voice_device_config.read(),
    }


@router.get("/config")
async def get_config() -> dict[str, Any]:
    return {
        "status": "ok",
        "config": voice_device_config.read(),
    }


@router.patch("/config")
async def update_config(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    return {
        "status": "updated",
        "config": await asyncio.to_thread(
            voice_device_config.update,
            payload,
        ),
    }


@router.post("/stt/transcribe")
async def transcribe(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    encoded = str(payload.get("audio_base64") or "")

    try:
        audio = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid base64 audio: {exc}",
        ) from exc

    try:
        return await asyncio.to_thread(
            offline_stt.transcribe_pcm16,
            audio,
            sample_rate=payload.get("sample_rate"),
            channels=payload.get("channels"),
            backend=payload.get("backend"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/tts/speak")
async def speak(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            offline_tts.speak,
            str(payload.get("text") or ""),
            backend=payload.get("backend"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/run")
async def run_qa() -> dict[str, Any]:
    return await asyncio.to_thread(voice_qa.run)


@router.get("/report")
async def qa_report() -> dict[str, Any]:
    return await asyncio.to_thread(voice_qa.run)
