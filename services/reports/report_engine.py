"""Daily, weekly, monthly, person, and household AI reports."""
from __future__ import annotations
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from .insight_engine import InsightEngine
from .models import ReportWindow

class ReportEngine:
    def __init__(self, learning_store: Any) -> None:
        self.store = learning_store
        self.insights = InsightEngine()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_day(value: Optional[str]) -> date:
        return date.fromisoformat(value) if value else datetime.now(timezone.utc).date()

    @staticmethod
    def _start(day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=timezone.utc)

    def _events(self, window: ReportWindow, limit: int = 50000) -> List[Dict[str, Any]]:
        return self.store.list_events(
            limit=limit,
            person_id=window.person_id,
            start_at=window.start_at.isoformat(),
            end_at=window.end_at.isoformat(),
        )

    @staticmethod
    def _hour(value: str) -> Optional[int]:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
        except (TypeError, ValueError):
            return None

    def _build(self, window: ReportWindow) -> Dict[str, Any]:
        events = self._events(window)
        rooms = Counter(e.get("room") or "unknown" for e in events)
        types = Counter(e.get("event_type") or "unknown" for e in events)
        people = Counter(e.get("person_id") or "unassigned" for e in events)
        hours = Counter(h for e in events if (h := self._hour(str(e.get("occurred_at", "")))) is not None)
        active_days = len({str(e.get("occurred_at", ""))[:10] for e in events if e.get("occurred_at")})
        duration_days = max(1, (window.end_at.date() - window.start_at.date()).days + 1)
        insight = self.insights.build(events, duration_days)
        return {
            "status": "ok",
            "service": "reports",
            "sprint": "9.5-half1",
            "report_type": window.report_type,
            "generated_at": self._utc_now().isoformat(),
            "person_id": window.person_id,
            "window": window.as_dict(),
            "summary": {
                "total_events": len(events),
                "active_days": active_days,
                "average_events_per_active_day": round(len(events) / max(1, active_days), 2),
                "unique_people": len([p for p in people if p != "unassigned"]),
                "unique_rooms": len([r for r in rooms if r != "unknown"]),
                "top_room": rooms.most_common(1)[0][0] if rooms else None,
                "top_event_type": types.most_common(1)[0][0] if types else None,
                "peak_hour_utc": hours.most_common(1)[0][0] if hours else None,
            },
            "breakdown": {
                "events_by_room": dict(rooms.most_common(30)),
                "events_by_type": dict(types.most_common(30)),
                "events_by_person": dict(people.most_common(30)),
                "events_by_hour_utc": {str(h): hours.get(h, 0) for h in range(24)},
            },
            "insights": insight,
        }

    def daily(self, day: Optional[str] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        selected = self._parse_day(day)
        start = self._start(selected)
        end = start + timedelta(days=1) - timedelta(microseconds=1)
        return self._build(ReportWindow("daily", start, end, person_id))

    def weekly(self, week_start: Optional[str] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        selected = self._parse_day(week_start)
        start_day = selected - timedelta(days=selected.weekday())
        start = self._start(start_day)
        end = start + timedelta(days=7) - timedelta(microseconds=1)
        return self._build(ReportWindow("weekly", start, end, person_id))

    def monthly(self, month: Optional[str] = None, person_id: Optional[str] = None) -> Dict[str, Any]:
        if month:
            selected = datetime.strptime(month, "%Y-%m").date().replace(day=1)
        else:
            selected = self._utc_now().date().replace(day=1)
        next_month = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)
        start = self._start(selected)
        end = self._start(next_month) - timedelta(microseconds=1)
        return self._build(ReportWindow("monthly", start, end, person_id))

    def person(self, person_id: str, days: int = 30) -> Dict[str, Any]:
        end = self._utc_now()
        start = end - timedelta(days=max(1, min(365, days)))
        report = self._build(ReportWindow("person", start, end, person_id))
        report["privacy_note"] = "This report summarizes only locally stored NoorBrain learning events."
        return report

    def household(self, days: int = 7) -> Dict[str, Any]:
        end = self._utc_now()
        start = end - timedelta(days=max(1, min(365, days)))
        report = self._build(ReportWindow("household", start, end, None))
        report["privacy_note"] = "Unassigned events are retained as aggregate household activity."
        return report

    def insight_summary(self, days: int = 30, person_id: Optional[str] = None) -> Dict[str, Any]:
        end = self._utc_now(); bounded = max(1, min(365, days)); start = end - timedelta(days=bounded)
        window = ReportWindow("insights", start, end, person_id)
        events = self._events(window)
        return {"status": "ok", "service": "reports", "report_type": "insights", "generated_at": end.isoformat(), "person_id": person_id, "window": window.as_dict(), "event_count": len(events), "insights": self.insights.build(events, bounded)}
