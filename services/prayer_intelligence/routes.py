from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from fastapi import APIRouter, Body, Query

from .service import prayer_intelligence_service, start_adhan_scheduler, stop_adhan_scheduler
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


@router.get("/adhan/settings")
async def adhan_settings() -> dict[str, Any]:
    """Return current Adhan configuration (enabled, target_node, media, scheduler).

    Truthful: if no verified Adhan media is configured/found, reports
    ADHAN_MEDIA_REQUIRED — never silently substitutes TTS or fabricated
    audio as Adhan.
    """
    from .service import adhan_scheduler_status
    cfg = await asyncio.to_thread(prayer_intelligence_service.adhan_settings)
    scheduler = adhan_scheduler_status()
    return {
        "status": "ok",
        **cfg,
        "scheduler_running": scheduler.get("running", False),
        "scheduler_interval_seconds": scheduler.get("interval_seconds", 30),
        "last_scheduler_check": scheduler.get("last_check"),
        "last_scheduler_result": scheduler.get("last_result"),
        "last_scheduler_error": scheduler.get("last_error"),
    }


@router.patch("/adhan/settings")
async def update_adhan_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Update Adhan configuration: enabled, target_node, lead_minutes, media_id."""
    changes = {}
    for key in ("adhan_enabled", "adhan_target_node",
                "adhan_lead_minutes", "adhan_media_id"):
        if key in payload:
            changes[key] = payload[key]
    await asyncio.to_thread(prayer_store.update_settings, changes)
    return {
        "status": "updated",
        **prayer_intelligence_service.adhan_settings(),
    }


@router.post("/adhan/test")
async def test_adhan() -> dict[str, Any]:
    """Manual one-shot Adhan playback for testing (e.g., phone Test Adhan button).

    Requirements:
    - Resolves ONLY validated category="adhan" media via adhan_settings()
    - Sends through authoritative Playback Router — no laptop fallback
    - Does NOT create a prayer "fired" dedup event
    - Does NOT alter the prayer schedule
    - Returns truthful played/failed result
    """
    from services.playback_router import playback_router
    cfg = await asyncio.to_thread(prayer_intelligence_service.adhan_settings)
    media_id = cfg.get("adhan_media_id")
    target_node = cfg.get("adhan_target_node")

    if not media_id:
        return {
            "status": "not_available",
            "media_state": cfg.get("media_state", prayer_intelligence_service.ADHAN_MEDIA_REQUIRED),
            "message": "No verified Adhan media available",
            "laptop_fallback": False,
        }

    if not target_node:
        return {
            "status": "not_available",
            "message": "No Adhan target node configured",
            "laptop_fallback": False,
        }

    try:
        playback_result = playback_router.play({
            "target_node": target_node,
            "type": "media",
            "media_id": media_id,
        })
        played = playback_result.get("status") in {"played", "accepted", "playing"}
        return {
            "status": "played" if played else "failed",
            "media_id": media_id,
            "target_node": target_node,
            "result": playback_result,
            "laptop_fallback": False,
            "fired_event_created": False,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "media_id": media_id,
            "target_node": target_node,
            "laptop_fallback": False,
            "fired_event_created": False,
        }


@router.post("/adhan/check")
async def check_adhan(
    payload: dict[str, Any] | None = Body(default=None),
) -> dict[str, Any]:
    """Poll for due prayers and attempt Adhan playback via Playback Router.

    All playback is routed through the authoritative Playback Router.
    No laptop audio fallback. No real network in tests (playback is patched).
    """
    return await asyncio.to_thread(
        prayer_intelligence_service.check_adhan_due,
        payload.get("now") if payload else None,
    )


@router.get("/adhan/scheduler")
async def adhan_scheduler() -> dict[str, Any]:
    """Return Adhan scheduler runtime truth."""
    from .service import adhan_scheduler_status
    return {
        "status": "ok",
        **adhan_scheduler_status(),
    }


@router.post("/adhan/scheduler/start")
async def start_scheduler() -> dict[str, Any]:
    """Start the automatic Adhan scheduler."""
    return await asyncio.to_thread(start_adhan_scheduler)


@router.post("/adhan/scheduler/stop")
async def stop_scheduler() -> dict[str, Any]:
    """Stop the automatic Adhan scheduler."""
    return await asyncio.to_thread(stop_adhan_scheduler)
