from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .runtime_bridge import voice_stack_status
from .tts_service import streaming_tts_service

router = APIRouter(
    prefix="/api/halo-voice-runtime",
    tags=["HALO Voice Runtime"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_voice_runtime",
        "version": "3.1-c1.6-c1.7",
        "stack": await asyncio.to_thread(voice_stack_status),
    }


@router.get("/status")
async def status() -> dict[str, Any]:
    return await asyncio.to_thread(voice_stack_status)


@router.post("/tts/start")
async def tts_start() -> dict[str, Any]:
    return await asyncio.to_thread(streaming_tts_service.start)


@router.post("/tts/stop")
async def tts_stop() -> dict[str, Any]:
    return await asyncio.to_thread(streaming_tts_service.stop)


@router.post("/tts/interrupt")
async def tts_interrupt() -> dict[str, Any]:
    return await asyncio.to_thread(streaming_tts_service.interrupt)


@router.post("/tts/speak")
async def tts_speak(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        item = await asyncio.to_thread(
            streaming_tts_service.enqueue,
            str(payload.get("text") or ""),
            priority=int(payload.get("priority", 0)),
            metadata=dict(payload.get("metadata") or {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    streaming_tts_service.start()

    return {
        "status": "queued",
        "item": item,
    }


@router.get("/tts/status")
async def tts_status() -> dict[str, Any]:
    return streaming_tts_service.status()


@router.get("/tts/queue")
async def tts_queue() -> dict[str, Any]:
    items = streaming_tts_service.queue()
    return {
        "status": "ok",
        "count": len(items),
        "items": items,
    }
