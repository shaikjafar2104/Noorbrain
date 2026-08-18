from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .engine import universal_voice_gateway


router = APIRouter(
    prefix="/api/universal-voice-v9",
    tags=["Universal Voice Gateway V9"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "universal_voice_gateway_v9",
        "version": "9.1.0",
        "runtime": universal_voice_gateway.status(),
    }


@router.get("/capabilities")
async def capabilities() -> dict[str, Any]:
    return {
        "status": "ready",
        "version": "9.1.0",
        "text_commands": True,
        "browser_speech_recognition": "client-detected",
        "audio_capture": "client-detected",
        "offline_transcription": "foundation",
        "conversation_context": True,
        "duplicate_protection": True,
    }


@router.post("/prepare")
async def prepare(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    transcript = str(payload.get("transcript") or "").strip()
    session_id = str(payload.get("session_id") or "default").strip()
    source = str(payload.get("source") or "text").strip()
    if not transcript:
        raise HTTPException(status_code=422, detail="Transcript is required.")
    try:
        result = await asyncio.to_thread(
            universal_voice_gateway.prepare,
            session_id,
            transcript,
            source,
        )
        return {"status": "ready" if result["accepted"] else "duplicate", **result}
    except Exception as error:
        universal_voice_gateway.record_error()
        raise HTTPException(
            status_code=503,
            detail=f"Voice gateway temporarily unavailable: {type(error).__name__}",
        ) from error


@router.post("/complete")
async def complete(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "default").strip()
    transcript = str(payload.get("transcript") or "").strip()
    response = str(payload.get("response") or "").strip()
    source = str(payload.get("source") or "voice").strip()
    if not transcript or not response:
        raise HTTPException(
            status_code=422,
            detail="Transcript and response are required.",
        )
    try:
        exchange = await asyncio.to_thread(
            universal_voice_gateway.complete,
            session_id,
            transcript,
            response,
            source,
        )
        return {"status": "remembered", "exchange": exchange}
    except Exception as error:
        universal_voice_gateway.record_error()
        raise HTTPException(
            status_code=503,
            detail=f"Voice memory temporarily unavailable: {type(error).__name__}",
        ) from error
