from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None


class ActivityAnalytics:
    def collect_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        try:
            from services.vision_intelligence.store import vision_event_store
            events.extend(vision_event_store.list(limit=5000))
        except Exception:
            pass

        try:
            from services.person_presence.store import presence_store
            events.extend(
                list(
                    reversed(
                        presence_store.read().get("events", [])
                    )
                )[:5000]
            )
        except Exception:
            pass

        try:
            from services.face_identity.store import face_identity_store
            for event in face_identity_store.list_events(limit=5000):
                events.append({
                    "id": event.get("id"),
                    "created_at": event.get("created_at"),
                    "event_type": (
                        "face_recognized"
                        if event.get("recognized")
                        else "unknown_face"
                    ),
                    "zone": event.get("zone"),
                    "person_id": event.get("person_id"),
                    "message": (
                        f"Recognized {event.get('person_name')}."
                        if event.get("recognized")
                        else "Unknown face detected."
                    ),
                    "confidence": event.get("confidence"),
                    "metadata": event.get("metadata", {}),
                    "source": "face_identity",
                })
        except Exception:
            pass

        deduped: dict[str, dict[str, Any]] = {}

        for event in events:
            key = str(
                event.get("id")
                or (
                    event.get("created_at"),
                    event.get("event_type"),
                    event.get("track_id"),
                    event.get("message"),
                )
            )
            deduped[key] = event

        result = list(deduped.values())
        result.sort(
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )
        return result

    def filtered(
        self,
        *,
        days: int = 30,
        event_type: str | None = None,
        zone: str | None = None,
        person_id: str | None = None,
        query: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query_fold = query.casefold() if query else None
        result = []

        for event in self.collect_events():
            created = _parse_time(event.get("created_at"))

            if created and created < cutoff:
                continue

            if event_type and str(
                event.get("event_type") or ""
            ).casefold() != event_type.casefold():
                continue

            if zone and str(
                event.get("zone") or ""
            ).casefold() != zone.casefold():
                continue

            if person_id and str(
                event.get("person_id") or ""
            ) != person_id:
                continue

            if query_fold:
                haystack = " ".join([
                    str(event.get("message") or ""),
                    str(event.get("event_type") or ""),
                    str(event.get("zone") or ""),
                    str(event.get("person_id") or ""),
                ]).casefold()

                if query_fold not in haystack:
                    continue

            result.append(event)

            if len(result) >= limit:
                break

        return result

    def summary(self, days: int = 30) -> dict[str, Any]:
        events = self.filtered(days=days, limit=5000)
        by_type = Counter()
        by_zone = Counter()
        by_person = Counter()
        by_day = Counter()
        by_hour = Counter()
        entry_count = 0
        exit_count = 0

        for event in events:
            event_type = str(event.get("event_type") or "unknown")
            zone = str(event.get("zone") or "unassigned")
            person = str(event.get("person_id") or "unknown")
            created = _parse_time(event.get("created_at"))

            by_type[event_type] += 1
            by_zone[zone] += 1
            by_person[person] += 1

            if event_type == "person_entered":
                entry_count += 1
            elif event_type == "person_exited":
                exit_count += 1

            if created:
                by_day[created.date().isoformat()] += 1
                by_hour[str(created.hour)] += 1

        return {
            "status": "ok",
            "days": days,
            "total_events": len(events),
            "entry_count": entry_count,
            "exit_count": exit_count,
            "by_type": dict(by_type.most_common()),
            "by_zone": dict(by_zone.most_common()),
            "by_person": dict(by_person.most_common()),
            "by_day": dict(sorted(by_day.items())),
            "by_hour": {
                str(hour): int(by_hour.get(str(hour), 0))
                for hour in range(24)
            },
        }

    def heatmap(self, days: int = 30) -> dict[str, Any]:
        events = self.filtered(days=days, limit=5000)
        matrix = {
            str(day): {str(hour): 0 for hour in range(24)}
            for day in range(7)
        }

        for event in events:
            created = _parse_time(event.get("created_at"))

            if not created:
                continue

            matrix[str(created.weekday())][str(created.hour)] += 1

        return {
            "status": "ok",
            "days": days,
            "weekdays": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
            "hours": list(range(24)),
            "matrix": matrix,
        }


activity_analytics = ActivityAnalytics()
