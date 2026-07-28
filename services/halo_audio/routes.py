from __future__ import annotations

import asyncio
import base64
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .buffer import audio_ring_buffer
from .config_store import audio_config_store
from .device_manager import audio_device_manager
from .models import AudioActionRequest
from .service import halo_audio_service

router = APIRouter(prefix="/api/halo-audio", tags=["HALO Audio"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return halo_audio_service.status()


@router.get("/status")
async def status() -> dict[str, Any]:
    return halo_audio_service.status()


@router.get("/devices")
async def devices() -> dict[str, Any]:
    return await asyncio.to_thread(
        audio_device_manager.list_devices,
    )


@router.get("/config")
async def get_config() -> dict[str, Any]:
    return {
        "status": "ok",
        "config": audio_config_store.read().model_dump(mode="json"),
    }


@router.patch("/config")
async def update_config(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    config = await asyncio.to_thread(
        audio_config_store.update,
        payload,
    )
    return {
        "status": "updated",
        "config": config.model_dump(mode="json"),
    }


@router.post("/start")
async def start(
    payload: AudioActionRequest = AudioActionRequest(),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_audio_service.start,
        payload.reason,
    )


@router.post("/stop")
async def stop(
    payload: AudioActionRequest = AudioActionRequest(),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_audio_service.stop,
        payload.reason,
    )


@router.post("/buffer/chunk")
async def append_chunk(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    encoded = str(payload.get("audio_base64") or "")

    try:
        chunk = base64.b64decode(encoded, validate=True)
        return audio_ring_buffer.append(chunk)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid audio payload: {exc}",
        ) from exc


@router.get("/buffer/status")
async def buffer_status() -> dict[str, Any]:
    return audio_ring_buffer.status()


@router.post("/buffer/clear")
async def buffer_clear() -> dict[str, Any]:
    removed = audio_ring_buffer.clear()
    return {
        "status": "cleared",
        "removed_chunks": removed,
    }
