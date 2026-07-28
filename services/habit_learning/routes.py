from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, Query
from .collector import habit_collector
from .pattern_engine import habit_pattern_engine
from .suggestion_engine import habit_suggestion_engine
from .store import habit_store

router = APIRouter(
    prefix="/api/habit-learning",
    tags=["Habit Learning"],
)

@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "habit_learning",
        "version": "3.9-d3-halves1-2",
        **habit_store.summary(),
    }

@router.post("/observe")
async def observe(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    item = await asyncio.to_thread(
        habit_collector.observe,
        event_type=str(payload.get("event_type") or "activity"),
        person_id=payload.get("person_id"),
        zone=payload.get("zone"),
        value=payload.get("value"),
        metadata=dict(payload.get("metadata") or {}),
    )
    return {"status": "created", "observation": item}

@router.post("/import-activity")
async def import_activity(days: int = 30) -> dict[str, Any]:
    return await asyncio.to_thread(habit_collector.import_activity, days)

@router.post("/patterns/rebuild")
async def rebuild_patterns() -> dict[str, Any]:
    return await asyncio.to_thread(habit_pattern_engine.rebuild)

@router.get("/patterns")
async def patterns(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    items = await asyncio.to_thread(habit_store.list, "patterns", limit)
    return {"status": "ok", "count": len(items), "patterns": items}

@router.post("/suggestions/generate")
async def generate_suggestions() -> dict[str, Any]:
    return await asyncio.to_thread(habit_suggestion_engine.generate)

@router.get("/suggestions")
async def suggestions(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    items = await asyncio.to_thread(habit_store.list, "suggestions", limit)
    return {"status": "ok", "count": len(items), "suggestions": items}

@router.get("/observations")
async def observations(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    items = await asyncio.to_thread(habit_store.list, "observations", limit)
    return {"status": "ok", "count": len(items), "observations": items}
