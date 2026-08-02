from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .store import conversation_memory_store


router = APIRouter(
    prefix="/api/halo-memory-v8",
    tags=["HALO Conversation Memory V8"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    data = await asyncio.to_thread(conversation_memory_store.read)
    return {
        "status": "healthy",
        "service": "halo_conversation_memory_v8",
        "version": "8.4.0",
        "sessions": len(data.get("sessions", {})),
    }


@router.post("/sessions/{session_id}/remember")
async def remember(
    session_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    role = str(payload.get("role") or "user").strip().lower()
    text = str(payload.get("text") or "").strip()
    if role not in {"user", "assistant", "system"}:
        raise HTTPException(status_code=422, detail="Invalid role.")
    if not text:
        raise HTTPException(status_code=422, detail="Text is required.")
    message = await asyncio.to_thread(
        conversation_memory_store.remember,
        session_id,
        role,
        text,
        payload.get("metadata") or {},
    )
    return {"status": "remembered", "message": message}


@router.put("/sessions/{session_id}/facts/{key}")
async def set_fact(
    session_id: str,
    key: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    if "value" not in payload:
        raise HTTPException(status_code=422, detail="Value is required.")
    facts = await asyncio.to_thread(
        conversation_memory_store.set_fact,
        session_id,
        key,
        payload["value"],
    )
    return {"status": "updated", "facts": facts}


@router.get("/sessions/{session_id}/context")
async def context(
    session_id: str,
    limit: int = Query(20, ge=1, le=200),
) -> dict[str, Any]:
    session = await asyncio.to_thread(
        conversation_memory_store.context,
        session_id,
        limit,
    )
    return {"status": "ok", "session": session}


@router.delete("/sessions/{session_id}")
async def clear(session_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        conversation_memory_store.clear,
        session_id,
    )
    return {"status": "cleared", "removed": removed}
