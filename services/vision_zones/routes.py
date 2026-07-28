from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .models import MotionSample, ZoneCreate
from .service import vision_zone_service
from .store import zone_store

router = APIRouter(
    prefix="/api/vision-zones",
    tags=["Vision Zones"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    zones = await asyncio.to_thread(zone_store.list_zones)
    events = await asyncio.to_thread(
        zone_store.list_motion_events,
        limit=1,
    )

    return {
        "status": "healthy",
        "service": "vision_zones",
        "version": "3.7-d1.2",
        "zone_count": len(zones),
        "motion_event_count": len(events),
    }


@router.get("/zones")
async def zones() -> dict[str, Any]:
    items = await asyncio.to_thread(zone_store.list_zones)

    return {
        "status": "ok",
        "count": len(items),
        "zones": items,
    }


@router.post("/zones")
async def create_zone(
    payload: ZoneCreate,
) -> dict[str, Any]:
    item = await asyncio.to_thread(
        zone_store.save_zone,
        payload.model_dump(mode="json"),
    )

    return {
        "status": "created",
        "zone": item,
    }


@router.delete("/zones/{zone_id}")
async def delete_zone(zone_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        zone_store.delete_zone,
        zone_id,
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Zone not found.",
        )

    return {
        "status": "deleted",
        "zone_id": zone_id,
    }


@router.post("/motion")
async def record_motion(
    payload: MotionSample,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        vision_zone_service.record_motion,
        camera_id=payload.camera_id,
        x=payload.x,
        y=payload.y,
        confidence=payload.confidence,
        source=payload.source,
        metadata=payload.metadata,
    )


@router.get("/motion")
async def motion_events(
    limit: int = Query(default=100, ge=1, le=1000),
    zone_id: str | None = None,
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        zone_store.list_motion_events,
        limit=limit,
        zone_id=zone_id,
    )

    return {
        "status": "ok",
        "count": len(items),
        "events": items,
    }


@router.post("/motion/clear")
async def clear_motion() -> dict[str, Any]:
    removed = await asyncio.to_thread(
        zone_store.clear_motion_events
    )

    return {
        "status": "cleared",
        "removed": removed,
    }
