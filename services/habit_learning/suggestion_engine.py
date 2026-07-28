from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .store import habit_store

class HabitSuggestionEngine:
    def generate(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        patterns = habit_store.list("patterns", limit=500)
        created = []

        for pattern in patterns:
            hour_distance = abs(int(pattern.get("hour", 0)) - now.hour)
            if hour_distance > 1:
                continue

            suggestion = habit_store.add("suggestions", {
                "kind": "habit_reminder",
                "person_id": pattern.get("person_id"),
                "zone": pattern.get("zone"),
                "priority": round(float(pattern.get("confidence", 0.5)), 3),
                "message": pattern.get("description"),
                "pattern_id": pattern.get("id"),
                "status": "new",
            })
            created.append(suggestion)

        return {
            "status": "ok",
            "created_count": len(created),
            "suggestions": created,
        }

habit_suggestion_engine = HabitSuggestionEngine()
