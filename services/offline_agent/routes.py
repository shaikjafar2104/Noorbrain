from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from .agent import offline_agent
from .cache import agent_cache
from .intent_router import intent_router
from .models import AgentRequest
from .tool_registry import tool_registry

router = APIRouter(prefix="/api/offline-agent", tags=["HALO Offline Agent"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_offline_agent",
        "mode": "local_fast",
        "tools": tool_registry.names(),
        "cache": "enabled",
    }


@router.post("/chat")
async def chat(payload: AgentRequest) -> dict[str, Any]:
    result = await asyncio.to_thread(
        offline_agent.process,
        payload.text,
        session_id=payload.session_id,
        confirm=payload.confirm,
    )
    return result.model_dump(mode="json")


@router.post("/intent")
async def inspect_intent(payload: AgentRequest) -> dict[str, Any]:
    intent = intent_router.route(payload.text)
    return {
        "status": "ok",
        "intent": intent.name,
        "arguments": intent.arguments,
        "confidence": intent.confidence,
    }


@router.get("/tools")
async def tools() -> dict[str, Any]:
    names = tool_registry.names()
    return {"status": "ok", "count": len(names), "tools": names}


@router.get("/skills/status")
async def skill_status() -> dict[str, Any]:
    result = await asyncio.to_thread(
        tool_registry.execute,
        "skills_status",
        {},
    )
    return result


@router.get("/home/status")
async def current_home_status() -> dict[str, Any]:
    result = await asyncio.to_thread(
        tool_registry.execute,
        "home_status",
        {},
    )
    return result


@router.post("/cache/clear")
async def clear_cache() -> dict[str, Any]:
    agent_cache.clear()
    return {"status": "cleared"}
