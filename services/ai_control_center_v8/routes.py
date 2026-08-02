from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/ai-control-center-v8",
    tags=["AI Control Center V8"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ai_control_center_v8",
        "version": "8.5.0",
    }


@router.get("/overview")
async def overview() -> dict[str, Any]:
    from services.halo_conversation_memory_v8.store import (
        conversation_memory_store,
    )

    memory = await asyncio.to_thread(conversation_memory_store.read)
    sessions = memory.get("sessions", {})
    message_count = sum(
        len(item.get("messages", []))
        for item in sessions.values()
    )
    fact_count = sum(
        len(item.get("facts", {}))
        for item in sessions.values()
    )

    routine = {
        "status": "unavailable",
        "activities": 0,
        "routines": 0,
        "habits": 0,
    }
    try:
        from services.routine_intelligence_v8.routes import health as routine_health
        routine = await routine_health()
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "8.5.0",
        "conversation_memory": {
            "sessions": len(sessions),
            "messages": message_count,
            "facts": fact_count,
        },
        "voice_context": {
            "status": "ready",
            "version": "8.4.1",
        },
        "routine_intelligence": routine,
    }
