from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response

from .analytics import activity_analytics
from .exporter import export_csv, export_json

router = APIRouter(
    prefix="/api/activity-intelligence",
    tags=["Activity Intelligence"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    summary = await asyncio.to_thread(
        activity_analytics.summary,
        30,
    )

    return {
        "status": "healthy",
        "service": "activity_intelligence",
        "version": "3.7-d1.5",
        "total_events": summary["total_events"],
    }


@router.get("/events")
async def events(
    days: int = Query(default=30, ge=1, le=365),
    event_type: str | None = None,
    zone: str | None = None,
    person_id: str | None = None,
    query: str | None = None,
    limit: int = Query(default=200, ge=1, le=5000),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        activity_analytics.filtered,
        days=days,
        event_type=event_type,
        zone=zone,
        person_id=person_id,
        query=query,
        limit=limit,
    )

    return {
        "status": "ok",
        "count": len(items),
        "events": items,
    }


@router.get("/summary")
async def summary(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        activity_analytics.summary,
        days,
    )


@router.get("/heatmap")
async def heatmap(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    return await asyncio.to_thread(
        activity_analytics.heatmap,
        days,
    )


@router.get("/export")
async def export(
    format: Literal["json", "csv"] = "json",
    days: int = Query(default=30, ge=1, le=365),
) -> Response:
    items = await asyncio.to_thread(
        activity_analytics.filtered,
        days=days,
        limit=5000,
    )

    if format == "csv":
        content = export_csv(items)
        media_type = "text/csv"
        filename = "noorbrain-activity.csv"
    else:
        content = export_json(items)
        media_type = "application/json"
        filename = "noorbrain-activity.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )
