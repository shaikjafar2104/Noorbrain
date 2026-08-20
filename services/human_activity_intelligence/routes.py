"""Human Activity Intelligence — FastAPI routes."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Query

from .adaptive_service import adaptive_rule_intelligence
from .engine import human_activity_intelligence, HumanActivityIntelligence
from .store import activity_store

router = APIRouter(prefix="/api/human-activity-intelligence", tags=["Human Activity Intelligence"])

# Initialize default settings if not present
def _ensure_default_settings():
    defaults = {
        "learning_enabled": "true",
        "activity_history_enabled": "true",
        "movement_start_seconds": "2",
        "movement_stop_seconds": "3",
        "stationary_threshold_seconds": "5",
        "long_stationary_seconds": "900",
        "long_sitting_seconds": "1800",
        "minimum_pattern_occurrences": "3",
        "proposal_cooldown_hours": "72",
        "automatic_rule_creation": "false",
        "snapshots_enabled": "false",
    }
    for key, value in defaults.items():
        if activity_store.get_setting(key) is None:
            activity_store.set_setting(key, value)

_ensure_default_settings()

# Backward-compatibility alias: routes written before engine refactor may call
# human_activity_intelligence.drainage(); map to the authoritative drain_events().
if not hasattr(human_activity_intelligence, "drainage"):
    human_activity_intelligence.drainage = human_activity_intelligence.drain_events  # type: ignore[attr-defined]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "human_activity_intelligence",
        "version": "1.0.0",
        "session_count": activity_store.session_count(),
        "event_count": activity_store.event_count(),
        "snapshot_enabled": activity_store.get_setting("snapshot_enabled") in {"1", "true", "yes"},
    }


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

@router.get("/settings")
async def settings() -> dict[str, Any]:
    return {
        "status": "ok",
        "settings": activity_store.get_all_settings(),
    }


@router.post("/settings")
async def update_settings(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    key = str(payload.get("key") or "").strip()
    value = str(payload.get("value") or "").strip()
    if not key:
        return {"status": "error", "detail": "key required"}
    activity_store.set_setting(key, value)
    return {"status": "updated", "key": key, "value": value}


# ------------------------------------------------------------------
# Observe — one person observation
# ------------------------------------------------------------------

@router.post("/observe")
async def observe(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    person_id = str(payload.get("person_id") or "").strip()
    track_id = payload.get("track_id")
    zone = str(payload.get("zone") or "").strip()
    room = str(payload.get("room") or zone).strip()
    box = payload.get("box")
    motion_delta = float(payload.get("motion_delta", 0.0))
    frame_epoch = payload.get("frame_epoch")
    observed_objects = payload.get("observed_objects")

    if not person_id:
        return {"status": "error", "detail": "person_id required"}

    events = human_activity_intelligence.observe(
        person_id=person_id,
        track_id=track_id,
        zone=zone,
        room=room,
        box=box,
        motion_delta=motion_delta,
        frame_epoch=frame_epoch,
        observed_objects=observed_objects,
    )

    return {
        "status": "ok",
        "person_id": person_id,
        "event_count": len(events),
        "events": events,
    }


# ------------------------------------------------------------------
# Observe batch — from the vision loop
# ------------------------------------------------------------------

@router.post("/observe-batch")
async def observe_batch(payload: list[dict[str, Any]] = Body(...)) -> dict[str, Any]:
    all_events: list[dict[str, Any]] = []
    for item in payload:
        person_id = str(item.get("person_id") or "").strip()
        if not person_id:
            continue
        evts = human_activity_intelligence.observe(
            person_id=person_id,
            track_id=item.get("track_id"),
            zone=str(item.get("zone") or "").strip(),
            room=str(item.get("room") or item.get("zone") or "").strip(),
            box=item.get("box"),
            motion_delta=float(item.get("motion_delta", 0.0)),
            frame_epoch=item.get("frame_epoch"),
            observed_objects=item.get("observed_objects"),
        )
        all_events.extend(evts)
    return {
        "status": "ok",
        "total_observed": len(payload),
        "event_count": len(all_events),
        "events": all_events,
    }


# ------------------------------------------------------------------
# Events — history
# ------------------------------------------------------------------

@router.get("/events")
async def events(
    event_type: str | None = Query(default=None),
    person_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = activity_store.list_events(
        event_type=event_type,
        person_id=person_id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return {
        "status": "ok",
        "count": len(items),
        "events": items,
    }


@router.get("/events/recent")
async def recent_events(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    items = activity_store.recent_events(limit=limit)
    return {"status": "ok", "count": len(items), "events": items}


@router.get("/events/count")
async def event_count() -> dict[str, Any]:
    return {"status": "ok", "count": activity_store.event_count()}


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

@router.get("/sessions")
async def sessions(
    person_id: str | None = Query(default=None),
    activity_type: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    items = activity_store.list_sessions(
        person_id=person_id,
        activity_type=activity_type,
        active=active,
        limit=limit,
    )
    return {"status": "ok", "count": len(items), "sessions": items}


@router.get("/sessions/active")
async def active_sessions() -> dict[str, Any]:
    items = activity_store.active_sessions()
    return {"status": "ok", "count": len(items), "sessions": items}


@router.get("/sessions/{session_id}")
async def session_detail(session_id: str) -> dict[str, Any]:
    items = activity_store.list_sessions(session_id=session_id, limit=1)
    if not items:
        return {"status": "not_found", "session_id": session_id}
    return {"status": "ok", "session": items[0]}


# ------------------------------------------------------------------
# Patterns
# ------------------------------------------------------------------

@router.get("/patterns")
async def patterns(
    person_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = activity_store.list_patterns(person_id=person_id, limit=limit)
    return {"status": "ok", "count": len(items), "patterns": items}


@router.get("/patterns/count")
async def pattern_count() -> dict[str, Any]:
    return {"status": "ok", "count": activity_store.pattern_count()}


@router.post("/patterns/rebuild")
async def rebuild_patterns(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    from .pattern_learner import rebuild_patterns as _rebuild

    return _rebuild(payload)


# ------------------------------------------------------------------
# Rule suggestions
# ------------------------------------------------------------------

@router.get("/suggestions")
async def suggestions(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = activity_store.list_suggestions(status=status, limit=limit)
    return {"status": "ok", "count": len(items), "suggestions": items}


@router.get("/suggestions/count")
async def suggestion_count() -> dict[str, Any]:
    return {"status": "ok", "count": activity_store.suggestion_count()}


@router.get("/suggestions/{suggestion_id}")
async def suggestion_detail(suggestion_id: str) -> dict[str, Any]:
    item = activity_store.get_suggestion(suggestion_id)
    if item is None:
        return {"status": "not_found", "suggestion_id": suggestion_id}
    return {"status": "ok", "suggestion": item}


@router.post("/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(suggestion_id: str) -> dict[str, Any]:
    result = activity_store.dismiss_suggestion(suggestion_id)
    if result is None:
        return {"status": "not_found", "suggestion_id": suggestion_id}
    return {"status": "dismissed", "suggestion": result}


@router.post("/suggestions/{suggestion_id}/snooze")
async def snooze_suggestion(suggestion_id: str, minutes: int = Query(default=30, ge=1, le=1440)) -> dict[str, Any]:
    result = activity_store.snooze_suggestion(suggestion_id, minutes)
    if result is None:
        return {"status": "not_found", "suggestion_id": suggestion_id}
    return {"status": "snoozed", "suggestion": result}


@router.post("/suggestions/{suggestion_id}/never-suggest")
async def never_suggest(suggestion_id: str) -> dict[str, Any]:
    result = activity_store.never_suggest(suggestion_id)
    if result is None:
        return {"status": "not_found", "suggestion_id": suggestion_id}
    return {"status": "never_suggest", "suggestion": result}


@router.post("/suggestions/{suggestion_id}/approve")
async def approve_suggestion(suggestion_id: str) -> dict[str, Any]:
    result = activity_store.approve_suggestion(suggestion_id)
    if result is None:
        return {"status": "not_found", "suggestion_id": suggestion_id}
    return {"status": "approved", "suggestion": result}


# ------------------------------------------------------------------
# Snapshots
# ------------------------------------------------------------------

@router.get("/snapshots")
async def snapshots(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, Any]:
    items = activity_store.list_snapshots(limit=limit)
    return {"status": "ok", "count": len(items), "snapshots": items}


@router.get("/snapshots/count")
async def snapshot_count() -> dict[str, Any]:
    return {"status": "ok", "count": activity_store.snapshot_count()}


@router.post("/snapshots")
async def snapshot_now() -> dict[str, Any]:
    snapshot = human_activity_intelligence.snapshot()
    saved = activity_store.save_snapshot(snapshot)
    return {
        "status": "ok",
        "snapshot": snapshot,
        "saved": saved is not None,
        "snapshot_enabled": activity_store.get_setting("snapshot_enabled") in {"1", "true", "yes"},
    }


# ------------------------------------------------------------------
# Background drain → rule pipeline (threading.Event based)
# ------------------------------------------------------------------

_drain_stop = threading.Event()
_drain_started = threading.Event()
_drain_lock = threading.Lock()


async def start_background_drain(interval_seconds: float = 2.0) -> dict[str, Any]:
    with _drain_lock:
        if _drain_started.is_set():
            return {"status": "already_running"}
        _drain_stop.clear()
        _drain_started.set()

        def _run() -> None:
            while not _drain_stop.wait(interval_seconds):
                try:
                    events = human_activity_intelligence.drain_events()
                    if events:
                        from services.reminder_rules import reminder_rules

                        for ev in events:
                            try:
                                reminder_rules.handle_event(ev)
                            except Exception:
                                pass
                except Exception:
                    pass

        thread = threading.Thread(target=_run, daemon=True, name="HAI-drain")
        thread.start()
        return {"status": "started", "interval_seconds": interval_seconds}


async def stop_background_drain(timeout: float = 5.0) -> dict[str, Any]:
    with _drain_lock:
        _drain_stop.set()
        _drain_started.clear()
    return {"status": "stopped"}


# ------------------------------------------------------------------
# Snapshot scheduler (threading.Event based)
# ------------------------------------------------------------------

_snapshot_stop = threading.Event()
_snapshot_started = threading.Event()
_snapshot_lock = threading.Lock()


async def start_snapshot_scheduler(interval_seconds: float = 300.0) -> dict[str, Any]:
    with _snapshot_lock:
        if _snapshot_started.is_set():
            return {"status": "already_running"}
        _snapshot_stop.clear()
        _snapshot_started.set()

        def _run() -> None:
            while not _snapshot_stop.wait(max(60.0, interval_seconds)):
                try:
                    if activity_store.get_setting("snapshot_enabled") in {"1", "true", "yes"}:
                        snapshot = human_activity_intelligence.snapshot()
                        activity_store.save_snapshot(snapshot)
                except Exception:
                    pass

        thread = threading.Thread(target=_run, daemon=True, name="HAI-snapshot")
        thread.start()
        return {"status": "started", "interval_seconds": interval_seconds}


async def stop_snapshot_scheduler(timeout: float = 5.0) -> dict[str, Any]:
    with _snapshot_lock:
        _snapshot_stop.set()
        _snapshot_started.clear()
    return {"status": "stopped"}


# ------------------------------------------------------------------
# Adaptive Rule Intelligence — pattern learning and approvals
# ------------------------------------------------------------------

@router.get("/adaptive-rules/health")
async def adaptive_health() -> dict[str, Any]:
    return adaptive_rule_intelligence.health()

@router.get("/adaptive-rules/status")
async def adaptive_status() -> dict[str, Any]:
    settings = activity_store.get_all_settings()
    return {
        "status": "ok",
        "learning_enabled": settings.get("learning_enabled", "true") in {"1", "true", "yes"},
        "automatic_rule_creation": settings.get("automatic_rule_creation", "false") in {"1", "true", "yes"},
        "pattern_count": activity_store.pattern_count(),
        "suggestion_count": activity_store.suggestion_count(),
        "event_count": activity_store.event_count(),
    }

@router.get("/adaptive-rules/activity")
async def adaptive_activity() -> dict[str, Any]:
    """Live human activity snapshot."""
    return human_activity_intelligence.snapshot()

@router.get("/adaptive-rules/timeline")
async def adaptive_timeline(
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = activity_store.recent_events(limit=limit)
    return {"status": "ok", "count": len(items), "events": items}

@router.get("/adaptive-rules/patterns")
async def adaptive_patterns(
    person_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    return adaptive_rule_intelligence.patterns(person_id=person_id, limit=limit)

@router.get("/adaptive-rules/proposals")
async def adaptive_proposals(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    return adaptive_rule_intelligence.suggestions(status=status, limit=limit)

@router.post("/adaptive-rules/patterns/rebuild")
async def adaptive_rebuild(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    result = adaptive_rule_intelligence.rebuild_patterns()
    sug_result = adaptive_rule_intelligence.generate_suggestions()
    return {
        "status": "ok",
        "patterns": result,
        "suggestions": sug_result,
    }

@router.post("/adaptive-rules/proposals/{proposal_id}/approve")
async def adaptive_approve(proposal_id: str) -> dict[str, Any]:
    return adaptive_rule_intelligence.approve_suggestion(proposal_id)

@router.post("/adaptive-rules/proposals/{proposal_id}/reject")
async def adaptive_reject(proposal_id: str) -> dict[str, Any]:
    return adaptive_rule_intelligence.reject_suggestion(proposal_id)

@router.patch("/adaptive-rules/proposals/{proposal_id}")
async def adaptive_patch_proposal(
    proposal_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Edit a proposal (message, cooldown, zone, etc.)."""
    result = activity_store.update_suggestion(proposal_id, payload)
    if result is None:
        return {"status": "error", "detail": "proposal not found"}
    return {"status": "updated", "proposal": result}

@router.get("/adaptive-rules/settings")
async def adaptive_settings() -> dict[str, Any]:
    return {"status": "ok", "settings": activity_store.get_all_settings()}

@router.patch("/adaptive-rules/settings")
async def adaptive_update_settings(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    key = str(payload.get("key") or "").strip()
    value = str(payload.get("value") or "").strip()
    if not key:
        return {"status": "error", "detail": "key required"}
    activity_store.set_setting(key, value)
    return {"status": "updated", "key": key, "value": value}


# ------------------------------------------------------------------
# Habits — Islamic practice streak tracking
# ------------------------------------------------------------------

DEFAULT_HABITS = [
    {"id": "habit-morning-adhkar", "name": "Morning Adhkar", "category": "dhikr",
     "target_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
     "trigger_type": None, "trigger_value": None},
    {"id": "habit-evening-ayat", "name": "Evening Ayat", "category": "quran",
     "target_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
     "trigger_type": None, "trigger_value": None},
    {"id": "habit-quran-reading", "name": "Quran Reading", "category": "quran",
     "target_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
     "trigger_type": "activity", "trigger_value": "long_sitting"},
    {"id": "habit-prayer-reminder", "name": "Prayer Posture Check", "category": "prayer",
     "target_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
     "trigger_type": "activity", "trigger_value": "sit_to_stand"},
]


def _ensure_default_habits() -> None:
    existing = activity_store.list_habits()
    existing_ids = {h["id"] for h in existing}
    for h in DEFAULT_HABITS:
        if h["id"] not in existing_ids:
            now_iso = _utc_now_iso()
            with activity_store._lock:
                conn = activity_store._ensure_connection()
                conn.execute(
                    """INSERT OR IGNORE INTO habits (
                        id, name, category, target_days, trigger_type, trigger_value,
                        created_at_iso, streak_current, streak_longest, completions_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, '[]')""",
                    (h["id"], h["name"], h["category"],
                     json.dumps(h["target_days"]), h.get("trigger_type"),
                     h.get("trigger_value"), now_iso),
                )
                conn.commit()


@router.get("/habits")
async def habits() -> dict[str, Any]:
    _ensure_default_habits()
    items = activity_store.list_habits()
    return {"status": "ok", "count": len(items), "habits": items}


@router.get("/habits/stats")
async def habit_stats() -> dict[str, Any]:
    """Return streak stats for the Islamic Habit Streak Tracker."""
    _ensure_default_habits()
    habits = activity_store.list_habits()
    total = len(habits)
    active_streaks = sum(1 for h in habits if h["streak_current"] > 0)
    return {
        "status": "ok",
        "total_habits": total,
        "active_streaks": active_streaks,
        "habits": [
            {
                "id": h["id"],
                "name": h["name"],
                "category": h["category"],
                "streak_current": h["streak_current"],
                "streak_longest": h["streak_longest"],
                "last_completed": h["last_completed_iso"],
                "badge": _habit_badge(h),
            }
            for h in habits
        ],
    }


def _habit_badge(habit: dict[str, Any]) -> str:
    """Return badge name based on streak length."""
    streak = habit.get("streak_current", 0)
    longest = habit.get("streak_longest", 0)
    if streak >= 30 or longest >= 30:
        return "gold"
    if streak >= 14 or longest >= 14:
        return "silver"
    if streak >= 7 or longest >= 7:
        return "bronze"
    return "none"


@router.get("/habits/{habit_id}")
async def habit_detail(habit_id: str) -> dict[str, Any]:
    _ensure_default_habits()
    items = activity_store.list_habits()
    for h in items:
        if h["id"] == habit_id:
            return {"status": "ok", "habit": h}
    return {"status": "not_found", "habit_id": habit_id}


@router.post("/habits/{habit_id}/complete")
async def habit_complete(habit_id: str) -> dict[str, Any]:
    _ensure_default_habits()
    result = activity_store.complete_habit(habit_id)
    if result is None:
        return {"status": "not_found", "habit_id": habit_id}
    return {"status": "completed", "habit": result}


@router.post("/habits/{habit_id}/reset")
async def habit_reset(habit_id: str) -> dict[str, Any]:
    _ensure_default_habits()
    result = activity_store.reset_habit_streak(habit_id)
    if result is None:
        return {"status": "not_found", "habit_id": habit_id}
    return {"status": "reset", "habit": result}


@router.post("/habits/upsert")
async def habit_upsert(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Create or update a habit with trigger configuration."""
    habit_id = str(payload.get("id") or "").strip()
    if not habit_id:
        return {"status": "error", "detail": "habit id required"}
    habit_data = {
        "id": habit_id,
        "name": payload.get("name", "Untitled Habit"),
        "category": payload.get("category", "other"),
        "target_days": payload.get("target_days", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]),
        "trigger_type": payload.get("trigger_type"),
        "trigger_value": payload.get("trigger_value"),
        "created_at_iso": payload.get("created_at_iso"),
    }
    result = activity_store.upsert_habit(habit_data)
    return {"status": "ok", "habit": result}


@router.delete("/habits/{habit_id}")
async def habit_delete(habit_id: str) -> dict[str, Any]:
    """Delete a habit permanently."""
    if habit_id in ("habit-morning-adhkar", "habit-evening-ayat", 
                    "habit-quran-reading", "habit-prayer-reminder"):
        return {"status": "error", "detail": "Cannot delete default habit. Use reset instead."}
    deleted = activity_store.delete_habit(habit_id)
    if not deleted:
        return {"status": "not_found", "habit_id": habit_id}
    return {"status": "deleted", "habit_id": habit_id}
