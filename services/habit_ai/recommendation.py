"""
============================================================
Project : NoorBrain
Module  : Habit Recommendation Engine
Sprint  : 4.3 + 4.4
Purpose :
    Generate safe reminder recommendations using locally
    learned habit data and current context.

This module does not directly play reminders.
It only returns a recommendation.
============================================================
"""

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional


class HabitRecommendationEngine:

    LEARNING_THRESHOLD = 20

    # --------------------------------------------------
    @staticmethod
    def _events(habits: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(habits, dict):
            return []

        for key in ("recent", "events", "history", "habits"):
            value = habits.get(key)

            if isinstance(value, list):
                return [
                    event
                    for event in value
                    if isinstance(event, dict)
                ]

        return []

    # --------------------------------------------------
    @staticmethod
    def _time_context(hour: int) -> str:
        if 5 <= hour < 12:
            return "morning"

        if 12 <= hour < 17:
            return "afternoon"

        if 17 <= hour < 21:
            return "evening"

        return "night"

    # --------------------------------------------------
    @staticmethod
    def _day_type(weekday: str) -> str:
        if weekday in {"Saturday", "Sunday"}:
            return "weekend"

        return "weekday"

    # --------------------------------------------------
    @staticmethod
    def _hour_distance(first: int, second: int) -> int:
        """
        Circular clock distance.

        Examples:
            23 and 0 = 1 hour
            22 and 1 = 3 hours
        """

        direct = abs(first - second)
        return min(direct, 24 - direct)

    # --------------------------------------------------
    @staticmethod
    def _clamp_confidence(value: float) -> float:
        return round(max(0.0, min(float(value), 100.0)), 1)

    # --------------------------------------------------
    def _learning_response(
        self,
        observations: int,
        appearance_count: int,
        current: datetime
    ) -> Dict[str, Any]:

        progress = min(
            100.0,
            (
                appearance_count
                / self.LEARNING_THRESHOLD
            ) * 100.0
        )

        return {
            "status": "learning",
            "recommendation": "learn_more",
            "should_play": False,
            "confidence_percent": self._clamp_confidence(
                progress
            ),
            "reason": (
                "NoorBrain is still collecting enough "
                "arrival history for a reliable recommendation."
            ),
            "observations": observations,
            "appearance_count": appearance_count,
            "minimum_appearances_required": (
                self.LEARNING_THRESHOLD
            ),
            "learning_progress_percent": round(
                progress,
                1
            ),
            "current_hour": current.hour,
            "current_weekday": current.strftime("%A"),
            "context": {
                "time_period": self._time_context(
                    current.hour
                ),
                "day_type": self._day_type(
                    current.strftime("%A")
                )
            }
        }

    # --------------------------------------------------
    def evaluate(
        self,
        habits: Dict[str, Any],
        now: Optional[datetime] = None
    ) -> Dict[str, Any]:

        current = now or datetime.now()
        events = self._events(habits)

        appeared_events = [
            event
            for event in events
            if event.get("type") == "appeared"
        ]

        disappeared_events = [
            event
            for event in events
            if event.get("type") == "disappeared"
        ]

        observations = len(events)
        appearance_count = len(appeared_events)

        if appearance_count < self.LEARNING_THRESHOLD:
            return self._learning_response(
                observations=observations,
                appearance_count=appearance_count,
                current=current
            )

        arrival_hours = []
        arrival_weekdays = []
        presence_durations = []

        for event in appeared_events:
            hour = event.get("hour")

            if isinstance(hour, int) and 0 <= hour <= 23:
                arrival_hours.append(hour)

            weekday = event.get("weekday")

            if isinstance(weekday, str) and weekday:
                arrival_weekdays.append(weekday)

        for event in disappeared_events:
            duration = event.get("duration")

            if (
                isinstance(duration, (int, float))
                and duration >= 0
            ):
                presence_durations.append(float(duration))

        if not arrival_hours:
            return self._learning_response(
                observations=observations,
                appearance_count=appearance_count,
                current=current
            )

        hour_counter = Counter(arrival_hours)
        expected_hour, expected_hour_count = (
            hour_counter.most_common(1)[0]
        )

        expected_weekday = None
        expected_weekday_count = 0

        if arrival_weekdays:
            weekday_counter = Counter(arrival_weekdays)

            (
                expected_weekday,
                expected_weekday_count
            ) = weekday_counter.most_common(1)[0]

        current_hour = current.hour
        current_weekday = current.strftime("%A")

        hour_distance = self._hour_distance(
            current_hour,
            expected_hour
        )

        hour_confidence = (
            expected_hour_count
            / len(arrival_hours)
        ) * 100.0

        weekday_confidence = 0.0

        if arrival_weekdays:
            weekday_confidence = (
                expected_weekday_count
                / len(arrival_weekdays)
            ) * 100.0

        hour_match = hour_distance <= 1
        weekday_match = (
            expected_weekday is None
            or current_weekday == expected_weekday
        )

        current_day_type = self._day_type(
            current_weekday
        )

        expected_day_type = (
            self._day_type(expected_weekday)
            if expected_weekday
            else current_day_type
        )

        day_type_match = (
            current_day_type == expected_day_type
        )

        data_strength = min(
            100.0,
            (
                appearance_count
                / 50.0
            ) * 100.0
        )

        score = (
            hour_confidence * 0.45
            + weekday_confidence * 0.20
            + data_strength * 0.20
        )

        if hour_match:
            score += 10.0

        if weekday_match:
            score += 3.0

        if day_type_match:
            score += 2.0

        confidence = self._clamp_confidence(score)

        if hour_match and day_type_match:
            recommendation = "play_now"
            should_play = True

            if weekday_match:
                reason = (
                    "Current time and day match the learned "
                    "arrival pattern."
                )
            else:
                reason = (
                    "Current time matches the learned arrival "
                    "pattern, although the weekday differs."
                )

        elif hour_distance == 2 and day_type_match:
            recommendation = "wait"
            should_play = False
            reason = (
                "The expected arrival period is close, but "
                "the strongest learned time has not arrived yet."
            )

        else:
            recommendation = "wait"
            should_play = False
            reason = (
                "Current context does not closely match the "
                "strongest learned arrival pattern."
            )

        average_presence_seconds = None

        if presence_durations:
            average_presence_seconds = round(
                sum(presence_durations)
                / len(presence_durations),
                1
            )

        return {
            "status": "ready",
            "mode": "stable",
            "recommendation": recommendation,
            "should_play": should_play,
            "confidence_percent": confidence,
            "reason": reason,
            "observations": observations,
            "appearance_count": appearance_count,
            "learning_progress_percent": 100.0,
            "current_hour": current_hour,
            "current_weekday": current_weekday,
            "expected_hour": expected_hour,
            "expected_time": f"{expected_hour:02d}:00",
            "expected_weekday": expected_weekday,
            "hour_distance": hour_distance,
            "average_presence_seconds": (
                average_presence_seconds
            ),
            "pattern_strength": {
                "hour_confidence_percent": round(
                    hour_confidence,
                    1
                ),
                "weekday_confidence_percent": round(
                    weekday_confidence,
                    1
                ),
                "data_strength_percent": round(
                    data_strength,
                    1
                )
            },
            "context": {
                "time_period": self._time_context(
                    current_hour
                ),
                "day_type": current_day_type,
                "expected_day_type": expected_day_type,
                "hour_match": hour_match,
                "weekday_match": weekday_match,
                "day_type_match": day_type_match
            }
        }


habit_recommendation = HabitRecommendationEngine()
