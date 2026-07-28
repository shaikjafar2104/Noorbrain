from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

class Scheduler:
    def due(self, schedule: dict[str, Any], now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        kind = str(schedule.get("kind") or "manual")

        if kind == "manual":
            return False

        if kind == "hourly":
            minute = int(schedule.get("minute", 0))
            return now.minute == minute

        if kind == "daily":
            hour = int(schedule.get("hour", 0))
            minute = int(schedule.get("minute", 0))
            return now.hour == hour and now.minute == minute

        if kind == "weekly":
            weekday = int(schedule.get("weekday", 0))
            hour = int(schedule.get("hour", 0))
            minute = int(schedule.get("minute", 0))
            return (
                now.weekday() == weekday
                and now.hour == hour
                and now.minute == minute
            )

        if kind == "interval":
            seconds = int(schedule.get("seconds", 60))
            last_run_at = schedule.get("last_run_at")
            if not last_run_at:
                return True

            last = datetime.fromisoformat(
                str(last_run_at).replace("Z", "+00:00")
            )
            return (now - last).total_seconds() >= seconds

        return False

scheduler = Scheduler()
