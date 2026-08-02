from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .engine import voice_context_engine


router = APIRouter(
    prefix="/api/halo-voice-context-v8",
    tags=["HALO Voice Context V8"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_voice_context_v8",
        "version": "8.4.1",
    }


@router.post("/context")
async def context(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "default").strip()
    utterance = str(payload.get("utterance") or "").strip()
    limit = int(payload.get("limit") or 12)
    if not utterance:
        raise HTTPException(status_code=422, detail="Utterance is required.")
    result = await asyncio.to_thread(
        voice_context_engine.build,
        session_id,
        utterance,
        max(1, min(limit, 50)),
    )
    return {"status": "ok", "context": result}


@router.post("/exchange")
async def exchange(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "default").strip()
    user_text = str(payload.get("user_text") or "").strip()
    assistant_text = str(payload.get("assistant_text") or "").strip()
    source = str(payload.get("source") or "voice").strip()
    if not user_text or not assistant_text:
        raise HTTPException(
            status_code=422,
            detail="User and assistant text are required.",
        )
    remembered = await asyncio.to_thread(
        voice_context_engine.remember_exchange,
        session_id,
        user_text,
        assistant_text,
        source,
    )
    return {"status": "remembered", "exchange": remembered}


@router.get("/sessions/{session_id}/context")
async def session_context(
    session_id: str,
    utterance: str = Query("Continue our conversation."),
    limit: int = Query(12, ge=1, le=50),
) -> dict[str, Any]:
    result = await asyncio.to_thread(
        voice_context_engine.build,
        session_id,
        utterance,
        limit,
    )
    return {"status": "ok", "context": result}
