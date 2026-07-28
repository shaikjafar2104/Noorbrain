from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from fastapi import APIRouter, Body, Query

from .service import prayer_intelligence_service
from .store import prayer_store

router = APIRouter(
    prefix="/api/prayer-intelligence",
    tags=["Prayer Intelligence"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    status = await asyncio.to_thread(
        prayer_intelligence_service.status
    )

    return {
        "status": "healthy",
        "service": "prayer_intelligence",
        "version": "1.0.0",
        "next_prayer": status["next_prayer"],
        "next_time": status["next_time"],
    }


@router.get("/settings")
async def settings() -> dict[str, Any]:
    return {
        "status": "ok",
        "settings": await asyncio.to_thread(
            prayer_intelligence_service.settings
        ),
    }


@router.patch("/settings")
async def update_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    updated = await asyncio.to_thread(
        prayer_store.update_settings,
        payload,
    )
    return {
        "status": "updated",
        "settings": updated,
    }


@router.get("/times")
async def times(
    prayer_date: date | None = Query(default=None),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        prayer_intelligence_service.times_for,
        prayer_date or date.today(),
    )


@router.get("/status")
async def status() -> dict[str, Any]:
    return await asyncio.to_thread(
        prayer_intelligence_service.status
    )


@router.get("/due")
async def due() -> dict[str, Any]:
    return await asyncio.to_thread(
        prayer_intelligence_service.due_events
    )


@router.post("/test")
async def test_prayer(
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    prayer = str(payload.get("prayer") or "maghrib")
    event = {
        "kind": "test",
        "prayer": prayer,
        "message": str(
            payload.get("message")
            or f"Prayer Intelligence test for {prayer.title()}."
        ),
    }
    delivery = await asyncio.to_thread(
        prayer_intelligence_service.speak_event,
        event,
    )
    return {
        "status": "ok",
        "event": event,
        "delivery": delivery,
    }


@router.post("/acknowledge")
async def acknowledge(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    item = await asyncio.to_thread(
        prayer_store.acknowledge,
        str(payload["prayer"]),
        str(payload.get("date") or date.today().isoformat()),
    )
    return {
        "status": "acknowledged",
        "item": item,
    }


@router.get("/events")
async def events(
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        prayer_store.list_events,
        limit,
    )
    return {
        "status": "ok",
        "count": len(items),
        "events": items,
    }
