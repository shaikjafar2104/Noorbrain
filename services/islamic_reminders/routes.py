from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, HTTPException, Query

from .service import islamic_reminder_service
from .store import islamic_reminder_store

router = APIRouter(
    prefix="/api/islamic-reminders",
    tags=["Islamic Reminder Intelligence"],
)

@router.get("/health")
async def health() -> dict[str, Any]:
    mappings = await asyncio.to_thread(islamic_reminder_store.list_mappings)
    events = await asyncio.to_thread(islamic_reminder_store.list_events, 1)
    return {
        "status": "healthy",
        "service": "islamic_reminders",
        "version": "1.0.0",
        "mapping_count": len(mappings),
        "event_count": len(events),
    }

@router.get("/mappings")
async def mappings() -> dict[str, Any]:
    items = await asyncio.to_thread(islamic_reminder_store.list_mappings)
    return {"status": "ok", "count": len(items), "mappings": items}

@router.post("/mappings")
async def create_mapping(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    item = await asyncio.to_thread(islamic_reminder_store.save_mapping, payload)
    return {"status": "created", "mapping": item}

@router.patch("/mappings/{mapping_id}")
async def update_mapping(mapping_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    existing = next(
        (item for item in islamic_reminder_store.list_mappings() if item.get("id") == mapping_id),
        None,
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Mapping not found.")
    item = await asyncio.to_thread(
        islamic_reminder_store.save_mapping,
        {**existing, **payload, "id": mapping_id},
    )
    return {"status": "updated", "mapping": item}

@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(islamic_reminder_store.delete_mapping, mapping_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Mapping not found.")
    return {"status": "deleted", "mapping_id": mapping_id}

@router.post("/evaluate")
async def evaluate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return await asyncio.to_thread(
        islamic_reminder_service.evaluate,
        event_type=str(payload.get("event_type") or "manual"),
        zone=payload.get("zone"),
        person_id=payload.get("person_id"),
        timezone_name=str(payload.get("timezone") or "America/Toronto"),
        metadata=dict(payload.get("metadata") or {}),
    )

@router.post("/trigger")
async def trigger(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return await asyncio.to_thread(islamic_reminder_service.trigger, payload)

@router.get("/events")
async def events(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    items = await asyncio.to_thread(islamic_reminder_store.list_events, limit)
    return {"status": "ok", "count": len(items), "events": items}
