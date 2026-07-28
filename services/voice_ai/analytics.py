from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


class VoiceAnalytics:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "voice.db"

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _top(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
        return [{"name": key, "count": count} for key, count in counter.most_common(limit)]

    def _rows(self, days: int, limit: int = 10000) -> list[sqlite3.Row]:
        if not self.db_path.is_file():
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 3650)))
        with self._connect() as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "voice_turns" not in tables:
                return []
            rows = conn.execute(
                "SELECT * FROM voice_turns ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 50000)),),
            ).fetchall()
        return [row for row in rows if (self._parse_time(row["created_at"]) or cutoff) >= cutoff]

    def summary(self, days: int = 30) -> Dict[str, Any]:
        days = max(1, min(days, 3650))
        rows = self._rows(days)
        intents: Counter[str] = Counter()
        rooms: Counter[str] = Counter()
        people: Counter[str] = Counter()
        hours: Counter[int] = Counter()
        daily: Counter[str] = Counter()
        user_chars = 0
        assistant_chars = 0

        for row in rows:
            intents[str(row["intent"] or "unknown")] += 1
            if row["room"]:
                rooms[str(row["room"])] += 1
            if row["person_id"]:
                people[str(row["person_id"])] += 1
            created = self._parse_time(row["created_at"])
            if created:
                hours[created.hour] += 1
                daily[created.date().isoformat()] += 1
            user_chars += len(str(row["user_text"] or ""))
            assistant_chars += len(str(row["assistant_text"] or ""))

        count = len(rows)
        active_days = len(daily)
        return {
            "status": "ok",
            "period_days": days,
            "database": str(self.db_path),
            "database_available": self.db_path.is_file(),
            "conversation_count": count,
            "active_days": active_days,
            "average_per_active_day": round(count / active_days, 2) if active_days else 0.0,
            "average_user_message_length": round(user_chars / count, 2) if count else 0.0,
            "average_assistant_message_length": round(assistant_chars / count, 2) if count else 0.0,
            "top_intents": self._top(intents),
            "top_rooms": self._top(rooms),
            "top_people": self._top(people),
            "peak_hour": hours.most_common(1)[0][0] if hours else None,
            "hourly_activity": [{"hour": hour, "count": hours.get(hour, 0)} for hour in range(24)],
            "daily_activity": [{"date": day, "count": daily[day]} for day in sorted(daily)],
        }

    def recent(self, limit: int = 20) -> Dict[str, Any]:
        limit = max(1, min(limit, 200))
        if not self.db_path.is_file():
            return {"status": "ok", "count": 0, "turns": []}
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT id, created_at, person_id, room, user_text, assistant_text, intent "
                    "FROM voice_turns ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return {"status": "ok", "count": len(rows), "turns": [dict(row) for row in rows]}
        except sqlite3.Error as exc:
            return {"status": "unavailable", "count": 0, "turns": [], "reason": str(exc)}


voice_analytics = VoiceAnalytics()
