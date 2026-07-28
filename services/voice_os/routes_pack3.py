from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, HTTPException

from .audio_devices import list_audio_devices
from .live_pipeline import live_voice_pipeline

router = APIRouter(prefix="/api/voice-os/live", tags=["Voice OS Live"])

@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "voice_os_live",
        "version": "3.0-phaseB-pack3",
        "audio": await asyncio.to_thread(list_audio_devices),
        "pipeline": live_voice_pipeline.status(),
    }

@router.get("/devices")
async def devices() -> dict[str, Any]:
    return await asyncio.to_thread(list_audio_devices)

@router.post("/configure")
async def configure(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return await asyncio.to_thread(live_voice_pipeline.configure, payload)

@router.post("/start")
async def start() -> dict[str, Any]:
    return await asyncio.to_thread(live_voice_pipeline.start)

@router.post("/stop")
async def stop() -> dict[str, Any]:
    return await asyncio.to_thread(live_voice_pipeline.stop)

@router.get("/status")
async def status() -> dict[str, Any]:
    return live_voice_pipeline.status()

@router.post("/transcript")
async def transcript(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            live_voice_pipeline.submit_transcript,
            str(payload.get("text") or ""),
            bool(payload.get("confirm", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
