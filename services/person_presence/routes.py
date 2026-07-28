from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, Query
from .service import person_presence_service
from .store import presence_store

router = APIRouter(prefix="/api/person-presence", tags=["Person Presence"])

@router.get("/health")
async def health() -> dict[str, Any]:
    summary = await asyncio.to_thread(person_presence_service.summary)
    return {"status": "healthy", "service": "person_presence", "version": "3.7-d1.3", "active_count": summary["active_count"]}

@router.post("/tracks")
async def update_track(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not str(payload.get("track_id") or "").strip():
        return {"status": "error", "detail": "track_id is required"}
    return await asyncio.to_thread(person_presence_service.update, payload)

@router.get("/tracks")
async def tracks() -> dict[str, Any]:
    return await asyncio.to_thread(person_presence_service.summary)

@router.post("/cleanup")
async def cleanup(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    return await asyncio.to_thread(person_presence_service.cleanup, float(payload.get("stale_after_seconds", 15)))

@router.get("/events")
async def events(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    items = list(reversed(presence_store.read()["events"]))[:limit]
    return {"status": "ok", "count": len(items), "events": items}
