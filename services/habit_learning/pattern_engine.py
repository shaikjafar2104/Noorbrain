from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any
from .store import habit_store

def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

class HabitPatternEngine:
    def rebuild(self) -> dict[str, Any]:
        observations = habit_store.list("observations", limit=5000)
        buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

        for item in observations:
            created = parse_time(
                item.get("metadata", {}).get("source_created_at")
                or item.get("created_at")
            )
            if not created:
                continue

            person = str(item.get("person_id") or "unknown")
            zone = str(item.get("zone") or "unassigned")
            event_type = str(item.get("event_type") or "activity")
            hour = str(created.hour)
            buckets[(person, zone, event_type, hour)].append(item)

        patterns = []
        for (person, zone, event_type, hour), items in buckets.items():
            if len(items) < 2:
                continue

            confidence = min(1.0, 0.35 + len(items) * 0.1)
            patterns.append({
                "id": f"{person}:{zone}:{event_type}:{hour}",
                "person_id": None if person == "unknown" else person,
                "zone": None if zone == "unassigned" else zone,
                "event_type": event_type,
                "hour": int(hour),
                "occurrences": len(items),
                "confidence": round(confidence, 3),
                "description": (
                    f"{event_type} often occurs in {zone} around {int(hour):02d}:00."
                ),
            })

        patterns.sort(
            key=lambda item: (
                float(item["confidence"]),
                int(item["occurrences"]),
            ),
            reverse=True,
        )
        habit_store.replace_patterns(patterns)

        return {
            "status": "rebuilt",
            "pattern_count": len(patterns),
            "patterns": patterns,
        }

habit_pattern_engine = HabitPatternEngine()
