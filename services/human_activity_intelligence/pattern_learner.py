"""
Human Activity Intelligence — pattern learner.

Lightweight statistical pattern learning: recurring activity,
usual time window, usual days, support count, confidence, room/zone.
Produces learned_patterns and rule_suggestions from activity events.

Testability: pass store= to use a temporary ActivityStore.
Production defaults to the global activity_store singleton.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from .store import activity_store


def rebuild_patterns(payload: dict[str, Any] | None = None, store: Any = None) -> dict[str, Any]:
    """Rebuild learned patterns from recent activity events.

    Args:
        payload: optional dict with event_limit.
        store: optional ActivityStore; defaults to production activity_store.
    """
    store = store or activity_store
    limit = int((payload or {}).get("event_limit", 2000))

    events = store.recent_events(limit=limit)

    buckets: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for ev in events:
        event_type = str(ev.get("event_type") or "unknown")
        if event_type in {"activity_started", "activity_ended", "activity_expired"}:
            continue
        person_id = str(ev.get("person_id") or "unknown")
        zone = str(ev.get("zone") or "unassigned")
        hour = str(datetime.fromtimestamp(ev.get("created_at_epoch", time.time()), tz=timezone.utc).hour)
        key = (person_id, zone, event_type, hour)
        buckets.setdefault(key, []).append(ev)

    patterns = []
    for (person_id, zone, event_type, hour), items in buckets.items():
        if len(items) < 2:
            continue
        confidence = min(1.0, 0.35 + len(items) * 0.1)
        pid = f"pat:{person_id}:{zone}:{event_type}:{hour}"
        patterns.append({
            "id": pid,
            "pattern_type": "activity_pattern",
            "person_id": None if person_id == "unknown" else person_id,
            "zone": None if zone == "unassigned" else zone,
            "activity_type": event_type,
            "hour": int(hour),
            "occurrences": len(items),
            "support_count": len(items),
            "confidence": round(confidence, 3),
            "description": f"{event_type} often occurs in {zone or 'an unassigned area'} around {int(hour):02d}:00.",
            "first_seen_iso": items[-1]["created_at_iso"],
            "last_seen_iso": items[0]["created_at_iso"],
            "usual_days": [],
            "usual_start_hour": int(hour),
            "usual_end_hour": int(hour),
        })
        store.add_pattern(patterns[-1])

    patterns.sort(key=lambda p: (p["confidence"], p["support_count"]), reverse=True)
    return {
        "status": "rebuilt",
        "pattern_count": len(patterns),
        "patterns": patterns,
    }


def generate_rule_suggestions(payload: dict[str, Any] | None = None, store: Any = None) -> dict[str, Any]:
    """Generate rule suggestions from learned patterns.

    Each suggestion is NEVER silently activated — user approval is mandatory.
    Default action_type is 'notification', never 'dua'.

    Args:
        payload: optional dict.
        store: optional ActivityStore; defaults to production activity_store.
    """
    store = store or activity_store
    patterns = store.list_patterns(limit=200)
    suggestions: list[dict[str, Any]] = []

    for pat in patterns:
        if pat.get("person_id") is None:
            continue
        if pat.get("zone") is None:
            continue
        if pat.get("confidence", 0.0) < 0.5:
            continue
        if pat.get("support_count", 0) < 3:
            continue

        # Map activity type → suggested rule trigger + default message
        trigger_map = {
            "sitting": "long_sitting",
            "standing": "activity_standing",
            "moving": "activity_moving",
            "stationary": "inactivity",
            "long_sitting": "long_sitting",
            "inactivity": "inactivity",
            "possible_phone_use": "possible_phone_use",
            "possible_tv_context": "possible_tv_context",
        }
        trigger = trigger_map.get(pat["activity_type"], pat["activity_type"])

        # Default suggestion messages (user-customizable when creating rule)
        message_map = {
            "long_sitting": "You have been sitting for a while. Consider taking a break and remembering Allah.",
            "inactivity": "No movement detected for a while. Consider stretching or taking a short walk.",
            "possible_phone_use": "Possible phone use detected. Consider a short digital detox and Dhikr.",
            "possible_tv_context": "Possible TV time. A short reminder could be helpful.",
            "activity_standing": "Standing activity detected.",
            "activity_moving": "Movement detected.",
        }

        sid = f"sug:{pat['id']}"
        suggestion = {
            "id": sid,
            "suggestion_type": "rule_suggestion",
            "pattern_id": pat["id"],
            "rule_name": f"{pat['activity_type'].title()} in {pat['zone']}",
            "rule_trigger": trigger,
            "rule_zone": pat["zone"],
            "rule_message": message_map.get(trigger, f"{pat['activity_type']} detected."),
            "rule_action_type": "notification",
            "rule_target_node": "",
            "rule_cooldown_seconds": 1800,
            "rule_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "priority": pat["confidence"],
            "status": "new",
            "never_suggest": False,
            "user_approved": False,
            "created_at_iso": datetime.now(timezone.utc).isoformat(),
            "updated_at_iso": datetime.now(timezone.utc).isoformat(),
        }
        saved = store.add_suggestion(suggestion)
        suggestions.append(saved)

    suggestions.sort(key=lambda s: s.get("priority", 0), reverse=True)
    return {
        "status": "ok",
        "created_count": len(suggestions),
        "suggestions": suggestions,
    }
