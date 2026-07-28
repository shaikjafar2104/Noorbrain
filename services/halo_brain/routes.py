from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from .brain import halo_brain
from .decision_engine import halo_decision_engine
from .memory_engine import halo_memory_engine
from .models import BrainRequest, DecisionRequest, MemoryWrite
from .proactive_engine import proactive_engine
from .store import halo_brain_store

router = APIRouter(
    prefix="/api/halo-brain",
    tags=["HALO Brain"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return await asyncio.to_thread(halo_brain.health)


@router.post("/process")
async def process(payload: BrainRequest) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_brain.process,
        text=payload.text,
        session_id=payload.session_id,
        person_id=payload.person_id,
        zone=payload.zone,
        confirm=payload.confirm,
        metadata=payload.metadata,
    )


@router.post("/decide")
async def decide(payload: DecisionRequest) -> dict[str, Any]:
    return await asyncio.to_thread(
        halo_decision_engine.decide,
        signal=payload.signal,
        person_id=payload.person_id,
        zone=payload.zone,
        metadata=payload.metadata,
    )


@router.post("/memories")
async def remember(payload: MemoryWrite) -> dict[str, Any]:
    memory = await asyncio.to_thread(
        halo_memory_engine.remember,
        kind=payload.kind,
        value=payload.value,
        person_id=payload.person_id,
        zone=payload.zone,
        importance=payload.importance,
        metadata=payload.metadata,
    )
    return {
        "status": "created",
        "memory": memory,
    }


@router.get("/memories")
async def memories(
    query: str | None = None,
    person_id: str | None = None,
    zone: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        halo_memory_engine.recall,
        query=query,
        person_id=person_id,
        zone=zone,
        limit=limit,
    )
    return {
        "status": "ok",
        "count": len(items),
        "memories": items,
    }


@router.post("/proactive/evaluate")
async def proactive() -> dict[str, Any]:
    return await asyncio.to_thread(
        proactive_engine.evaluate
    )


@router.get("/decisions")
async def decisions(
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        halo_brain_store.list,
        "decisions",
        limit,
    )
    return {
        "status": "ok",
        "count": len(items),
        "decisions": items,
    }


@router.get("/executions")
async def executions(
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        halo_brain_store.list,
        "executions",
        limit,
    )
    return {
        "status": "ok",
        "count": len(items),
        "executions": items,
    }
