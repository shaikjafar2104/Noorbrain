from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .store import voice_platform_store


router = APIRouter(prefix="/api/voice-platform-v9", tags=["Voice Platform V9"])


@router.get("/health")
async def health() -> dict[str, Any]:
    try:
        from services.universal_voice_gateway_v9.engine import universal_voice_gateway
        runtime = universal_voice_gateway.status()
    except Exception:
        runtime = {"accepted": 0, "duplicates_blocked": 0, "errors": 0}
    return {
        "status": "healthy",
        "service": "voice_platform_v9",
        "version": "9.6.0",
        "gateway": runtime,
    }


@router.get("/config")
async def config() -> dict[str, Any]:
    data = await asyncio.to_thread(voice_platform_store.read)
    return {"status": "ok", "config": data}


@router.patch("/config")
async def update_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    settings = await asyncio.to_thread(voice_platform_store.update_settings, payload)
    return {"status": "updated", "config": settings}


@router.post("/profiles/{profile_id}/select")
async def select_profile(profile_id: str) -> dict[str, Any]:
    try:
        data = await asyncio.to_thread(voice_platform_store.select_profile, profile_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Voice profile not found.") from error
    return {"status": "selected", "config": data}


@router.post("/sessions/start")
async def start_session(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    source = str(payload.get("source") or "browser")
    session = await asyncio.to_thread(voice_platform_store.start_session, source)
    return {"status": "started", "session": session}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> dict[str, Any]:
    session = await asyncio.to_thread(voice_platform_store.end_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Voice session not found.")
    return {"status": "ended", "session": session}
