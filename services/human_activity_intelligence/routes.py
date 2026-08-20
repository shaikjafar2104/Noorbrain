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

# ------------------------------------------------------------------
# Islamic Stories Library (Feature 3 — HALO Islamic Story Mode)
# ------------------------------------------------------------------

ISLAMIC_STORIES: dict[str, dict[str, Any]] = {
    "prophet-yusuf": {
        "title": "The Story of Prophet Yusuf (Joseph)",
        "summary": "Prophet Yusuf was betrayed by his brothers who threw him into a well. He was sold into slavery, rose to power in Egypt, and forgave his brothers during famine.",
        "categories": ["quran", "prophet"],
        "surah_reference": "Surah Yusuf (Quran 12)",
    },
    "prophet-musa": {
        "title": "The Story of Prophet Musa (Moses)",
        "summary": "Prophet Musa was saved from the river as a baby, grew in Pharaoh's court, led the Exodus, and received the Torah on Mount Sinai.",
        "categories": ["quran", "prophet"],
        "surah_reference": "Surah Ash-Shu'ara (Quran 26), Surah Al-Qasas (Quran 28)",
    },
    "prophet-ibrahim": {
        "title": "The Story of Prophet Ibrahim (Abraham)",
        "summary": "Prophet Ibrahim was tested by Allah with trials of sacrifice and was willing to sacrifice his son. He was the first monotheist and a friend of Allah.",
        "categories": ["quran", "prophet"],
        "surah_reference": "Surah As-Saffat (Quran 37)",
    },
    "prophet-yunus": {
        "title": "The Story of Prophet Yunus (Jonah)",
        "summary": "Prophet Yunus was swallowed by a great fish after his people rejected him. He spent time in the darkness of the fish, repented, and was saved by Allah.",
        "categories": ["quran", "prophet"],
        "surah_reference": "Surah Al-Anbiya (Quran 21:87-88)",
    },
    "prophet-ayub": {
        "title": "The Story of Prophet Ayub (Job)",
        "summary": "Prophet Ayub was tested with loss of wealth, family, and health. He remained patient and faithful, and Allah restored everything to him double.",
        "categories": ["quran", "prophet"],
        "surah_reference": "Surah Al-Anbiya (Quran 21), Surah Al-Hajj (Quran 22)",
    },
    "prophet-dawud": {
        "title": "The Story of Prophet Dawud (David) and Sulaiman",
        "summary": "Prophet Dawud was a wise king who received the Psalms (Zabur). His son Sulaiman (Solomon) inherited his kingdom and was given the ability to communicate with jinn, animals, and birds.",
        "categories": ["quran", "prophet"],
        "surah_reference": "Surah Sad (Quran 38)",
    },
    "prophet-isa": {
        "title": "The Story of Prophet Isa (Jesus)",
        "summary": "Prophet Isa was born of the Virgin Maryam (Mary) through Allah's miracle. He spoke in the cradle, healed the sick, and was raised up to Allah. He foretold the coming of the Final Messenger.",
        "categories": ["quran", "prophet"],
        "surah_reference": "Surah Maryam (Quran 19), Surah Al-Imran (Quran 3)",
    },
    "prophet-muhammad": {
        "title": "The Story of Prophet Muhammad ﷺ (Seerah)",
        "summary": "The Final Messenger of Allah was born in Mecca, received revelation at age 40 in the cave of Hira, migrated to Medina, and brought the complete message of Islam.",
        "categories": ["seerah", "prophet"],
        "surah_reference": "Surah Al-Mu'minun (Quran 23), Surah Al-Qalam (Quran 68)",
    },
    "salah-guide": {
        "title": "The Guide to Salah (Prayer)",
        "summary": "Prayer is one of the five pillars of Islam. The Prophet Muhammad ﷣said: 'The first matter for which a servant will be brought to account on the Day of Judgment is his prayer.'",
        "categories": ["worship", "guide"],
        "surah_reference": "Surah Al-Baqarah (Quran 2:183-187)",
    },
    "fasting-guide": {
        "title": "The Guide to Sawm (Fasting)",
        "summary": "Fasting in Ramadan is the third pillar of Islam. It teaches patience, gratitude, and empathy for the less fortunate.",
        "categories": ["worship", "guide"],
        "surah_reference": "Surah Al-Baqarah (Quran 2:183-185)",
    },
    "zakat-guide": {
        "title": "The Guide to Zakat (Charity)",
        "summary": "Zakat is the third pillar and purifies wealth, cleansing greed from the heart. It is 2.5% of surplus wealth above nisab.",
        "categories": ["worship", "guide"],
        "surah_reference": "Surah At-Tawbah (Quran 9:60)",
    },
    "hajj-guide": {
        "title": "The Guide to Hajj (Pilgrimage)",
        "summary": "Hajj is the fifth pillar, performed once in a lifetime by those who are able. It symbolizes unity and equality before Allah.",
        "categories": ["worship", "guide"],
        "surah_reference": "Surah Al-Hajj (Quran 22)",
    },
}

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


@router.get("/timeline/categorized")
async def timeline_categorized(
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """Return semantically categorized activity timeline.

    Categories: prayer, prayer_prep, cooking, reading_quran,
    sleep_preparation, morning_routine, other
    """
    items = activity_store.categorized_timeline(limit=limit)
    category_summary = {}
    for ev in items:
        cat = ev["category"]
        category_summary[cat] = category_summary.get(cat, 0) + 1
    return {
        "status": "ok",
        "count": len(items),
        "category_summary": category_summary,
        "events": items,
    }

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
     "trigger_type": "time", "trigger_value": None,
     "trigger_time_start": "05:00", "trigger_time_end": "07:00"},
    {"id": "habit-evening-ayat", "name": "Evening Ayat", "category": "quran",
     "target_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
     "trigger_type": "time", "trigger_value": None,
     "trigger_time_start": "18:00", "trigger_time_end": "20:00"},
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
                        trigger_time_start, trigger_time_end,
                        created_at_iso, streak_current, streak_longest, completions_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, '[]')""",
                    (h["id"], h["name"], h["category"],
                     json.dumps(h["target_days"]), h.get("trigger_type"),
                     h.get("trigger_value"), h.get("trigger_time_start"),
                     h.get("trigger_time_end"), now_iso),
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
        "trigger_time_start": payload.get("trigger_time_start"),
        "trigger_time_end": payload.get("trigger_time_end"),
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


# ------------------------------------------------------------------
# Prayer Zone Presence Detection
# ------------------------------------------------------------------

@router.get("/prayer-zones")
async def prayer_zones() -> dict[str, Any]:
    _ensure_default_habits()
    zones = activity_store.list_prayer_zones()
    return {"status": "ok", "count": len(zones), "zones": zones}


@router.post("/prayer-zones/{zone_name}")
async def prayer_zone_upsert(zone_name: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Configure a prayer zone for DND + lighting automation."""
    zone = activity_store.upsert_prayer_zone(
        zone_name,
        enabled=payload.get("enabled", True),
        prayer_time_padding_seconds=payload.get("prayer_time_padding_seconds", 300),
        dnd_duration_minutes=payload.get("dnd_duration_minutes", 30),
        lighting_scene=payload.get("lighting_scene"),
    )
    return {"status": "ok", "zone": zone}


@router.delete("/prayer-zones/{zone_name}")
async def prayer_zone_delete(zone_name: str) -> dict[str, Any]:
    deleted = activity_store.delete_prayer_zone(zone_name)
    if not deleted:
        return {"status": "not_found", "zone_name": zone_name}
    return {"status": "deleted", "zone_name": zone_name}


@router.get("/prayer-zones/{zone_name}/trigger-status")
async def prayer_zone_trigger_status(zone_name: str) -> dict[str, Any]:
    """Check if a prayer zone would currently be triggered."""
    zone = activity_store.get_prayer_zone(zone_name)
    if not zone:
        return {"status": "not_found", "zone_name": zone_name}
    return {"status": "ok", "zone": zone, "currently_active": False}


# ------------------------------------------------------------------
# Islamic Stories — Feature 3: HALO Islamic Story Mode
# ------------------------------------------------------------------

@router.get("/stories")
async def list_stories(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> dict[str, Any]:
    """List available Islamic stories, optionally filtered by category or search term."""
    items = []
    for key, story in ISLAMIC_STORIES.items():
        cats = story.get("categories", [])
        if category and category not in cats:
            continue
        title = story["title"].lower()
        summary = story["summary"].lower()
        if search and search.lower() not in title and search.lower() not in summary and search.lower() not in key:
            continue
        items.append({
            "id": key,
            "title": story["title"],
            "categories": cats,
            "surah_reference": story["surah_reference"],
        })
    return {"status": "ok", "count": len(items), "stories": items}


@router.get("/stories/{story_id}")
async def get_story(story_id: str) -> dict[str, Any]:
    """Get full story content by ID."""
    story = ISLAMIC_STORIES.get(story_id)
    if not story:
        # Fuzzy search by topic
        for key, s in ISLAMIC_STORIES.items():
            if story_id.lower() in key.lower() or story_id.lower() in s["title"].lower():
                story = s
                story_id = key
                break
    if not story:
        return {"status": "not_found", "story_id": story_id}
    return {"status": "ok", "id": story_id, "story": story}


@router.post("/stories/search")
async def search_stories(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Search stories by keyword (for HALO story mode queries)."""
    query = str(payload.get("query", "")).strip().lower()
    results = []
    # Common spelling variants for Islamic names
    SPELLING_VARIANTS = {
        "yousuf": ["yusuf"],
        "yusuf": ["yousuf"],
        "yousef": ["yusuf", "yousuf"],
        "musab": ["musa", "moses"],
        "moosa": ["musa", "moses"],
        "isa": ["isa", "jesus"],
        "yahya": ["yahya", "john"],
        "dawud": ["dawud", "david"],
        "sulaiman": ["sulaiman", "solomon"],
        "ibrahim": ["ibrahim", "abraham"],
        "yunus": ["yunus", "jonah"],
        "ayub": ["ayub", "job"],
        "adam": ["adam"],
    }
    search_terms = [query]
    if query in SPELLING_VARIANTS:
        search_terms.extend(SPELLING_VARIANTS[query])

    for key, story in ISLAMIC_STORIES.items():
        title = story["title"].lower()
        summary = story["summary"].lower()
        cats = " ".join(story.get("categories", []))
        # Check all search terms (including variants)
        if any(term in title or term in summary or term in key or term in cats for term in search_terms):
            results.append({
                "id": key,
                "title": story["title"],
                "summary": story["summary"],
                "categories": story["categories"],
            })
    return {"status": "ok", "count": len(results), "results": results}


# ------------------------------------------------------------------
# Child Safety Zones (Extension of Prayer Zone infrastructure)
# ------------------------------------------------------------------

# Default child safety zones
DEFAULT_CHILD_SAFETY_ZONES = [
    {"zone_name": "Nursery", "enabled": True, "alert_type": "notify",
     "notification_message": "Child detected in nursery zone", "dnd_duration_minutes": 5,
     "lighting_scene": "warm-dim", "requires_acknowledgment": True},
    {"zone_name": "Kitchen", "enabled": True, "alert_type": "immediate",
     "notification_message": "⚠️ Child in kitchen! Please supervise immediately.", "dnd_duration_minutes": 0,
     "lighting_scene": None, "requires_acknowledgment": True},
    {"zone_name": "Stairs", "enabled": True, "alert_type": "immediate",
     "notification_message": "⚠️ Child near stairs! Please ensure safety gates are closed.", "dnd_duration_minutes": 0,
     "lighting_scene": "bright", "requires_acknowledgment": True},
]


def _ensure_default_child_zones() -> None:
    existing = activity_store.list_child_safety_zones()
    existing_names = {z["zone_name"] for z in existing}
    for z in DEFAULT_CHILD_SAFETY_ZONES:
        if z["zone_name"] not in existing_names:
            activity_store.upsert_child_safety_zone(**z)


@router.get("/child-safety-zones")
async def child_safety_zones() -> dict[str, Any]:
    _ensure_default_child_zones()
    zones = activity_store.list_child_safety_zones()
    return {"status": "ok", "count": len(zones), "zones": zones}


@router.post("/child-safety-zones/{zone_name}")
async def child_safety_zone_upsert(zone_name: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Configure a child safety zone."""
    zone = activity_store.upsert_child_safety_zone(
        zone_name,
        enabled=payload.get("enabled", True),
        alert_type=payload.get("alert_type", "notify"),
        notification_message=payload.get("notification_message"),
        dnd_duration_minutes=payload.get("dnd_duration_minutes", 5),
        lighting_scene=payload.get("lighting_scene"),
        requires_acknowledgment=payload.get("requires_acknowledgment", False),
    )
    return {"status": "ok", "zone": zone}


@router.delete("/child-safety-zones/{zone_name}")
async def child_safety_zone_delete(zone_name: str) -> dict[str, Any]:
    deleted = activity_store.delete_child_safety_zone(zone_name)
    if not deleted:
        return {"status": "not_found", "zone_name": zone_name}
    return {"status": "deleted", "zone_name": zone_name}


# ------------------------------------------------------------------
# Aura Teen Monitoring API
# ------------------------------------------------------------------

@router.get("/aura/teen-dashboard/{teen_name}")
async def teen_dashboard(teen_name: str) -> dict[str, Any]:
    """Get full teen dashboard data: current location, recent activity, curfew status."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    recent = activity_store.list_events(limit=50)
    # Filter events related to this teen
    teen_events = [e for e in recent if e.get("person_id", "").startswith(teen_name.lower())
                   or e.get("metadata", {}).get("person_name", "").lower() == teen_name.lower()
                   or e.get("metadata", {}).get("person_type") == "teen"]

    last_event = teen_events[0] if teen_events else None

    return {
        "status": "ok",
        "teen_name": teen_name,
        "current_zone": last_event.get("zone", "Unknown") if last_event else "Unknown",
        "last_seen_iso": last_event.get("created_at_iso", "Never") if last_event else "Never",
        "current_status": "active" if last_event else "unknown",
        "events": teen_events[:20],
        "is_home": any(e.get("zone", "").lower() in ("home", "house", "bedroom") for e in teen_events[:5]),
        "timestamp": now.isoformat(),
    }


@router.get("/aura/teen-presence")
async def teen_presence(zone: str = Query(default=""), person_type: str = Query(default="teen")) -> dict[str, Any]:
    """Check if any teen is present in a given zone."""
    events = activity_store.list_events(limit=20)
    teens_in_zone = []
    for ev in events:
        if ev.get("metadata", {}).get("person_type") == person_type:
            if not zone or ev.get("zone", "").lower() == zone.lower():
                teens_in_zone.append(ev)
    return {
        "status": "ok",
        "presence_detected": len(teens_in_zone) > 0,
        "count": len(teens_in_zone),
        "events": teens_in_zone[:5],
    }


@router.get("/aura/curfew-status/{teen_name}")
async def curfew_status(teen_name: str) -> dict[str, Any]:
    """Check curfew status for a teen."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    hour = now.hour

    # Default curfew rules (can be extended to per-teen config)
    weekday_curfew = 21  # 9 PM
    weekend_curfew = 22  # 10 PM

    is_weekend = now.weekday() >= 5
    curfew_hour = weekend_curfew if is_weekend else weekday_curfew
    is_past_curfew = hour >= curfew_hour

    # Check if teen is home
    try:
        dashboard = await teen_dashboard(teen_name)
        is_home = dashboard.get("is_home", False)
    except Exception:
        is_home = False

    return {
        "status": "ok",
        "teen_name": teen_name,
        "current_time": now.isoformat(),
        "is_weekend": is_weekend,
        "curfew_hour": curfew_hour,
        "is_past_curfew": is_past_curfew,
        "is_home": is_home,
        "status_message": "At home ✅" if is_home and not is_past_curfew else
                          "Past curfew ⚠️" if is_past_curfew and not is_home else
                          "Curfew check OK",
        "minutes_until_curfew": max(0, (curfew_hour - hour) * 60 - now.minute) if not is_past_curfew else 0,
    }


@router.get("/aura/emergency-alerts")
async def emergency_alerts() -> dict[str, Any]:
    """List recent emergency alerts and safety events."""
    events = activity_store.list_events(limit=50)
    alerts = [e for e in events if e.get("event_type", "").startswith("child_safety")
              or e.get("metadata", {}).get("alert_type") == "immediate"]
    return {
        "status": "ok",
        "count": len(alerts),
        "alerts": alerts[:10],
    }


@router.post("/aura/safety-check/{teen_name}")
async def safety_check_in(teen_name: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Teen sends a safety check-in ping to parents."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    message = payload.get("message", "I'm safe ✅")
    location = payload.get("location", "Unknown")

    activity_store.add_event({
        "event_type": "safety_check_in",
        "person_id": teen_name.lower(),
        "track_id": f"safety-{int(now.timestamp() * 1000)}",
        "zone": location,
        "room": location,
        "session_id": "manual",
        "confidence": 1.0,
        "duration_seconds": 0.0,
        "metadata": {
            "person_type": "teen",
            "person_name": teen_name,
            "message": message,
            "check_in": True,
        },
    })
    return {"status": "ok", "message": f"Check-in received from {teen_name}", "timestamp": now.isoformat()}
