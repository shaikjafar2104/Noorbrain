"""Explainable metrics and recommendations for NoorBrain reports."""
from __future__ import annotations
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List
from .models import Score

class InsightEngine:
    PRAYER_WORDS = ("fajr", "dhuhr", "zuhr", "asr", "maghrib", "isha", "prayer", "salah")

    @staticmethod
    def _event_day(event: Dict[str, Any]) -> str:
        return str(event.get("occurred_at", ""))[:10]

    def habit_score(self, events: List[Dict[str, Any]], window_days: int) -> Score:
        active_days = len({self._event_day(e) for e in events if self._event_day(e)})
        coverage = (active_days / max(1, window_days)) * 100
        volume_component = min(100.0, len(events) * 2.5)
        value = coverage * 0.72 + volume_component * 0.28
        confidence = min(100.0, active_days * 8.0 + len(events) * 0.5)
        return Score(value=value, confidence=confidence, sample_size=len(events))

    def prayer_score(self, events: List[Dict[str, Any]], window_days: int) -> Score:
        prayer_events = [e for e in events if any(word in str(e.get("event_type", "")).lower() for word in self.PRAYER_WORDS)]
        prayer_days = len({self._event_day(e) for e in prayer_events if self._event_day(e)})
        # Score measures observed consistency, not religious compliance.
        value = min(100.0, (prayer_days / max(1, window_days)) * 100)
        confidence = min(100.0, len(prayer_events) * 5.0 + prayer_days * 7.0)
        return Score(value=value, confidence=confidence, sample_size=len(prayer_events))

    def learning_confidence(self, events: List[Dict[str, Any]], window_days: int) -> Score:
        active_days = len({self._event_day(e) for e in events if self._event_day(e)})
        people = len({e.get("person_id") for e in events if e.get("person_id")})
        rooms = len({e.get("room") for e in events if e.get("room")})
        value = min(100.0, active_days * 7.0 + min(35.0, len(events) * 0.35) + min(15.0, (people + rooms) * 2.5))
        return Score(value=value, confidence=value, sample_size=len(events))

    def trend(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_day = Counter(self._event_day(e) for e in events if self._event_day(e))
        ordered = sorted(by_day.items())
        if len(ordered) < 4:
            return {"direction": "insufficient_data", "change_percent": 0.0, "reason": "At least four active days are needed."}
        midpoint = max(1, len(ordered) // 2)
        old = sum(v for _, v in ordered[:midpoint]) / midpoint
        new_count = len(ordered[midpoint:])
        new = sum(v for _, v in ordered[midpoint:]) / max(1, new_count)
        change = 0.0 if old == 0 else ((new - old) / old) * 100
        direction = "stable"
        if change >= 10: direction = "increasing"
        elif change <= -10: direction = "decreasing"
        return {"direction": direction, "change_percent": round(change, 2), "older_daily_average": round(old, 2), "recent_daily_average": round(new, 2)}

    def build(self, events: List[Dict[str, Any]], window_days: int) -> Dict[str, Any]:
        habit = self.habit_score(events, window_days)
        prayer = self.prayer_score(events, window_days)
        confidence = self.learning_confidence(events, window_days)
        trend = self.trend(events)
        rooms = Counter(e.get("room") for e in events if e.get("room"))
        types = Counter(str(e.get("event_type", "unknown")) for e in events)
        recommendations: List[str] = []
        if confidence.value < 35:
            recommendations.append("Collect events across more days before enabling automatic high-impact decisions.")
        if not rooms:
            recommendations.append("Attach room names to events to improve occupancy and routine insights.")
        if prayer.sample_size == 0:
            recommendations.append("No prayer-related events were observed in this period; prayer insight remains unavailable.")
        if trend["direction"] == "decreasing":
            recommendations.append("Recent activity is lower than the earlier baseline; review camera uptime and routine changes.")
        if not recommendations:
            recommendations.append("The learning baseline is healthy; continue monitoring for meaningful drift.")
        return {
            "habit_score": habit.as_dict(),
            "prayer_consistency": prayer.as_dict(),
            "learning_confidence": confidence.as_dict(),
            "trend": trend,
            "top_room": rooms.most_common(1)[0][0] if rooms else None,
            "top_event_type": types.most_common(1)[0][0] if types else None,
            "recommendations": recommendations,
        }
