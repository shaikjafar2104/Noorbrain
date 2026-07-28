from __future__ import annotations
from typing import Any
from .store import habit_store

class HabitCollector:
    def observe(
        self,
        *,
        event_type: str,
        person_id: str | None,
        zone: str | None,
        value: Any,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return habit_store.add("observations", {
            "event_type": event_type,
            "person_id": person_id,
            "zone": zone,
            "value": value,
            "metadata": metadata,
        })

    def import_activity(self, days: int = 30) -> dict[str, Any]:
        try:
            from services.activity_intelligence.analytics import activity_analytics
            events = activity_analytics.filtered(days=days, limit=5000)
        except Exception:
            events = []

        imported = 0
        existing = {
            (
                item.get("metadata", {}).get("source_event_id"),
                item.get("event_type"),
            )
            for item in habit_store.list("observations", limit=5000)
        }

        for event in events:
            key = (event.get("id"), event.get("event_type"))
            if key in existing:
                continue

            habit_store.add("observations", {
                "event_type": event.get("event_type") or "activity",
                "person_id": event.get("person_id"),
                "zone": event.get("zone"),
                "value": event.get("message"),
                "metadata": {
                    "source": "activity_intelligence",
                    "source_event_id": event.get("id"),
                    "source_created_at": event.get("created_at"),
                },
            })
            imported += 1

        return {
            "status": "ok",
            "imported": imported,
            "total_source_events": len(events),
        }

habit_collector = HabitCollector()
