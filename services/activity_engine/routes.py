from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(
    prefix="/api/activity",
    tags=["Activity"],
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_engine() -> Any:
    try:
        from . import activity_engine as module
    except Exception:
        return None

    for name in (
        "activity_engine",
        "engine",
        "activity_monitor",
        "monitor",
    ):
        candidate = getattr(module, name, None)
        if candidate is not None:
            return candidate

    return module


def call_without_blocking(
    target: Any,
    method_names: tuple[str, ...],
    *args: Any,
    **kwargs: Any,
) -> Any:
    if target is None:
        return None

    for name in method_names:
        method = getattr(target, name, None)

        if not callable(method):
            continue

        try:
            signature = inspect.signature(method)

            if "limit" in signature.parameters:
                return method(limit=kwargs.get("limit", 100))

            return method(*args)
        except TypeError:
            try:
                return method()
            except Exception:
                continue
        except Exception:
            continue

    return None


def extract_events(engine: Any, limit: int) -> list[Any]:
    result = call_without_blocking(
        engine,
        (
            "get_activities",
            "list_activities",
            "get_events",
            "list_events",
            "recent",
            "recent_events",
            "history",
        ),
        limit=limit,
    )

    if isinstance(result, dict):
        for key in (
            "activities",
            "events",
            "items",
            "data",
            "results",
        ):
            value = result.get(key)
            if isinstance(value, list):
                return value[-limit:]

    if isinstance(result, list):
        return result[-limit:]

    for attribute in (
        "activities",
        "events",
        "history",
        "_activities",
        "_events",
    ):
        value = getattr(engine, attribute, None)

        if isinstance(value, list):
            return value[-limit:]

        if hasattr(value, "__iter__") and not isinstance(
            value,
            (str, bytes, dict),
        ):
            try:
                return list(value)[-limit:]
            except Exception:
                pass

    return []


def normalize_event(
    event: Any,
    index: int,
) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        raw = event.model_dump(mode="json")
    elif hasattr(event, "dict"):
        raw = event.dict()
    elif isinstance(event, dict):
        raw = dict(event)
    else:
        raw = {
            key: value
            for key, value in vars(event).items()
            if not key.startswith("_")
        } if hasattr(event, "__dict__") else {
            "message": str(event)
        }

    event_type = (
        raw.get("event_type")
        or raw.get("type")
        or raw.get("activity_type")
        or raw.get("name")
        or "activity"
    )

    timestamp = (
        raw.get("timestamp")
        or raw.get("created_at")
        or raw.get("time")
        or utc_now()
    )

    normalized = {
        **raw,
        "id": str(
            raw.get("id")
            or raw.get("event_id")
            or f"activity-{index}"
        ),
        "event_type": str(event_type),
        "type": str(event_type),
        "timestamp": timestamp,
        "created_at": timestamp,
        "person_id": raw.get("person_id"),
        "person_name": (
            raw.get("person_name")
            or raw.get("name")
        ),
        "zone": raw.get("zone"),
        "room": raw.get("room"),
        "active": bool(raw.get("active", False)),
    }

    return normalized


def active_people_count(
    engine: Any,
    activities: list[dict[str, Any]],
) -> int:
    for attribute in (
        "active_people",
        "active_persons",
        "present_people",
        "current_people",
    ):
        value = getattr(engine, attribute, None)

        if isinstance(value, int):
            return value

        if isinstance(value, (list, set, tuple, dict)):
            return len(value)

    people = {
        str(item.get("person_id"))
        for item in activities
        if item.get("active")
        and item.get("person_id") is not None
    }
    return len(people)


@router.get("/health")
async def activity_health() -> dict[str, Any]:
    engine = load_engine()

    return {
        "status": "healthy",
        "service": "activity_api",
        "engine_loaded": engine is not None,
    }


@router.get("/activities")
async def activities(
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    engine = load_engine()
    raw_events = extract_events(engine, limit)

    items = [
        normalize_event(event, index)
        for index, event in enumerate(raw_events)
    ]

    active_count = active_people_count(
        engine,
        items,
    )

    engine_status = (
        "running"
        if engine is not None
        else "unavailable"
    )

    return {
        "status": "ok",
        "engine_status": engine_status,
        "engine": engine_status,
        "active_people": active_count,
        "active_count": active_count,
        "recorded_events": len(items),
        "total_events": len(items),
        "count": len(items),
        "activities": items,
        "events": items,
    }


@router.post("/activities/clear")
async def clear_activities() -> dict[str, Any]:
    engine = load_engine()
    cleared = False

    result = call_without_blocking(
        engine,
        (
            "clear_activities",
            "clear_events",
            "clear",
            "reset",
        ),
    )

    if result is not None:
        cleared = True

    if not cleared and engine is not None:
        for attribute in (
            "activities",
            "events",
            "history",
            "_activities",
            "_events",
        ):
            value = getattr(engine, attribute, None)

            if hasattr(value, "clear"):
                try:
                    value.clear()
                    cleared = True
                except Exception:
                    pass

    return {
        "status": "cleared",
        "cleared": cleared,
    }
