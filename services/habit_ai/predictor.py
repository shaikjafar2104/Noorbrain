from collections import Counter
from datetime import datetime


class HabitPredictor:

    def _events(self, habits):
        if not isinstance(habits, dict):
            return []

        for key in ("recent", "events", "history", "habits"):
            value = habits.get(key)
            if isinstance(value, list):
                return value

        return []

    def predict(self, habits):
        events = self._events(habits)

        hours = []
        weekdays = []
        durations = []

        for event in events:
            if not isinstance(event, dict):
                continue

            hour = event.get("hour")
            if isinstance(hour, int) and 0 <= hour <= 23:
                hours.append(hour)

            weekday = event.get("weekday")
            if isinstance(weekday, str) and weekday:
                weekdays.append(weekday)

            duration = event.get("duration")
            if isinstance(duration, (int, float)) and duration >= 0:
                durations.append(float(duration))

            timestamp = (
                event.get("timestamp")
                or event.get("time")
                or event.get("created_at")
            )

            if timestamp and not isinstance(hour, int):
                try:
                    parsed = datetime.fromisoformat(
                        str(timestamp).replace("Z", "+00:00")
                    )
                    hours.append(parsed.hour)
                    weekdays.append(parsed.strftime("%A"))
                except (ValueError, TypeError):
                    pass

        predictions = []

        if hours:
            likely_hour, count = Counter(hours).most_common(1)[0]
            confidence = round((count / len(hours)) * 100, 1)

            predictions.append({
                "type": "likely_appearance_time",
                "hour": likely_hour,
                "display_time": f"{likely_hour:02d}:00",
                "confidence_percent": confidence
            })

        if weekdays:
            likely_day, count = Counter(weekdays).most_common(1)[0]
            confidence = round((count / len(weekdays)) * 100, 1)

            predictions.append({
                "type": "likely_active_day",
                "weekday": likely_day,
                "confidence_percent": confidence
            })

        if durations:
            average_duration = round(sum(durations) / len(durations), 1)

            predictions.append({
                "type": "expected_presence_duration",
                "seconds": average_duration
            })

        return {
            "status": "ready" if predictions else "learning",
            "observations": len(events),
            "predictions": predictions
        }


habit_predictor = HabitPredictor()
