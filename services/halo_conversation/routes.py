from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from .engine import halo_conversation_engine
from .models import ConversationRequest
from .session_manager import conversation_sessions

router = APIRouter(
    prefix="/api/halo-conversation",
    tags=["HALO Conversation"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_conversation",
        "version": "3.2-c2.1-c2.3",
        "features": [
            "session_manager",
            "context_resolver",
            "clarification_engine",
        ],
        "session_count": len(conversation_sessions.list()),
    }


@router.post("/chat")
async def chat(payload: ConversationRequest) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_conversation_engine.process,
        payload.text,
        session_id=payload.session_id,
        confirm=payload.confirm,
    )


@router.get("/sessions")
async def sessions() -> dict[str, Any]:
    items = await asyncio.to_thread(conversation_sessions.list)
    return {
        "status": "ok",
        "count": len(items),
        "sessions": items,
    }


@router.get("/sessions/{session_id}")
async def session(session_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "session": await asyncio.to_thread(
            conversation_sessions.get,
            session_id,
        ),
    }


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        conversation_sessions.clear,
        session_id,
    )
    return {
        "status": "deleted",
        "session_id": session_id,
        "removed": removed,
    }
