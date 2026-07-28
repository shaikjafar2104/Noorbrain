from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .service import personalized_halo_service
from .store import personalized_halo_store

router = APIRouter(
    prefix="/api/personalized-halo",
    tags=["Personalized HALO"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    data = await asyncio.to_thread(
        personalized_halo_store.read
    )

    return {
        "status": "healthy",
        "service": "personalized_halo",
        "version": "1.0.0",
        "event_count": len(data["events"]),
        "enabled": data["settings"].get(
            "enabled",
            True,
        ),
    }


@router.get("/settings")
async def settings() -> dict[str, Any]:
    data = await asyncio.to_thread(
        personalized_halo_store.read
    )

    return {
        "status": "ok",
        "settings": data["settings"],
    }


@router.patch("/settings")
async def update_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    updated = await asyncio.to_thread(
        personalized_halo_store.update_settings,
        payload,
    )

    return {
        "status": "updated",
        "settings": updated,
    }


@router.post("/compose")
async def compose(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            personalized_halo_service.compose,
            person_id=str(payload["person_id"]),
            zone=payload.get("zone"),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.post("/greet")
async def greet(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            personalized_halo_service.greet,
            person_id=str(payload["person_id"]),
            zone=payload.get("zone"),
            force=bool(payload.get("force", False)),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get("/events")
async def events(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        personalized_halo_store.list_events,
        limit,
    )

    return {
        "status": "ok",
        "count": len(items),
        "events": items,
    }
