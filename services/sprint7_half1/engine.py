"""NoorBrain Sprint 7 Half 1 local intelligence engine.

Stores activity observations locally and provides:
- person intelligence
- habit learning
- daily timeline
- reminder suggestions
"""
from __future__ import annotations

import sqlite3
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "data" / "sprint7_intelligence.db"


class Sprint7Intelligence:
    ALLOWED_EVENTS = {
        "appeared", "entered_zone", "moved_zone", "left_zone",
        "stayed", "disappeared",
    }

    def __init__(self, database_path: Path = DEFAULT_DB) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path), timeout=30, check_same_thread=False
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS activity_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    person_id TEXT NOT NULL,
                    zone TEXT,
                    previous_zone TEXT,
                    duration REAL,
                    confidence REAL,
                    occurred_at REAL NOT NULL,
                    local_date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    weekday INTEGER NOT NULL,
                    source TEXT NOT NULL DEFAULT 'vision'
                );
                CREATE INDEX IF NOT EXISTS idx_s7_person_time
                    ON activity_observations(person_id, occurred_at DESC);
                CREATE INDEX IF NOT EXISTS idx_s7_zone_time
                    ON activity_observations(zone, occurred_at DESC);
                CREATE INDEX IF NOT EXISTS idx_s7_type_time
                    ON activity_observations(event_type, occurred_at DESC);
                """
            )

    @staticmethod
    def _person_id(value: Any) -> str:
        if value is None or str(value).strip() == "":
            return "unknown"
        return str(value).strip()

    def observe(self, event: dict[str, Any], source: str = "vision") -> dict[str, Any] | None:
        event_type = str(event.get("type") or "").strip()
        if event_type not in self.ALLOWED_EVENTS:
            return None

        timestamp = float(event.get("timestamp") or time.time())
        local = datetime.fromtimestamp(timestamp)
        person_id = self._person_id(event.get("person_id"))
        zone = event.get("zone")
        previous_zone = event.get("previous_zone")
        duration = event.get("duration")
        confidence = event.get("confidence")

        try:
            duration = None if duration is None else float(duration)
        except (TypeError, ValueError):
            duration = None
        try:
            confidence = None if confidence is None else float(confidence)
        except (TypeError, ValueError):
            confidence = None

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO activity_observations (
                    event_type, person_id, zone, previous_zone, duration,
                    confidence, occurred_at, local_date, hour, weekday, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type, person_id, zone, previous_zone, duration,
                    confidence, timestamp, local.strftime("%Y-%m-%d"),
                    local.hour, local.weekday(), source,
                ),
            )
            observation_id = cursor.lastrowid

        return {
            "id": observation_id,
            "event_type": event_type,
            "person_id": person_id,
            "zone": zone,
            "previous_zone": previous_zone,
            "duration": duration,
            "occurred_at": timestamp,
            "source": source,
        }

    def health(self) -> dict[str, Any]:
        with self._connect() as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM activity_observations"
            ).fetchone()[0]
            latest = connection.execute(
                "SELECT MAX(occurred_at) FROM activity_observations"
            ).fetchone()[0]
        return {
            "status": "healthy",
            "service": "sprint7_half1",
            "database": str(self.database_path),
            "observations": count,
            "latest_observation_at": latest,
        }

    def timeline(
        self,
        *,
        date: str | None = None,
        person_id: str | None = None,
        zone: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        clauses: list[str] = []
        values: list[Any] = []
        if date:
            clauses.append("local_date = ?")
            values.append(date)
        if person_id:
            clauses.append("person_id = ?")
            values.append(self._person_id(person_id))
        if zone:
            clauses.append("zone = ?")
            values.append(zone)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        values.append(max(1, min(int(limit), 1000)))

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, event_type, person_id, zone, previous_zone, duration,
                       confidence, occurred_at, local_date, hour, weekday, source
                FROM activity_observations
                {where}
                ORDER BY occurred_at DESC
                LIMIT ?
                """,
                values,
            ).fetchall()

        events = [dict(row) for row in rows]
        return {"count": len(events), "events": events}

    def people(self, days: int = 30) -> dict[str, Any]:
        since = time.time() - max(1, min(days, 3650)) * 86400
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT person_id,
                       MIN(occurred_at) AS first_seen,
                       MAX(occurred_at) AS last_seen,
                       COUNT(*) AS observation_count,
                       COUNT(DISTINCT local_date) AS active_days
                FROM activity_observations
                WHERE occurred_at >= ?
                GROUP BY person_id
                ORDER BY last_seen DESC
                """,
                (since,),
            ).fetchall()

        people: list[dict[str, Any]] = []
        for row in rows:
            person = dict(row)
            detail = self.person(person["person_id"], days=days)
            person.update({
                "top_zone": detail.get("top_zone"),
                "typical_arrival_hour": detail.get("typical_arrival_hour"),
                "average_presence_seconds": detail.get("average_presence_seconds"),
            })
            people.append(person)
        return {"days": days, "count": len(people), "people": people}

    def person(self, person_id: str, days: int = 30) -> dict[str, Any]:
        person_id = self._person_id(person_id)
        since = time.time() - max(1, min(days, 3650)) * 86400
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM activity_observations
                WHERE person_id = ? AND occurred_at >= ?
                ORDER BY occurred_at ASC
                """,
                (person_id, since),
            ).fetchall()
        observations = [dict(row) for row in rows]
        arrivals = [row for row in observations if row["event_type"] in {"appeared", "entered_zone"}]
        departures = [row for row in observations if row["event_type"] == "disappeared"]
        zone_counts = Counter(row["zone"] for row in observations if row.get("zone"))
        hour_counts = Counter(row["hour"] for row in arrivals)
        durations = [row["duration"] for row in departures if row.get("duration") is not None]
        active_dates = sorted({row["local_date"] for row in observations})

        return {
            "person_id": person_id,
            "days": days,
            "observation_count": len(observations),
            "first_seen": observations[0]["occurred_at"] if observations else None,
            "last_seen": observations[-1]["occurred_at"] if observations else None,
            "active_days": len(active_dates),
            "visit_count": len(arrivals),
            "top_zone": zone_counts.most_common(1)[0][0] if zone_counts else None,
            "zone_counts": dict(zone_counts),
            "typical_arrival_hour": hour_counts.most_common(1)[0][0] if hour_counts else None,
            "average_presence_seconds": round(sum(durations) / len(durations), 1) if durations else None,
            "recent": list(reversed(observations[-20:])),
        }

    def habits(self, days: int = 30, minimum_samples: int = 2) -> dict[str, Any]:
        since = time.time() - max(1, min(days, 3650)) * 86400
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT person_id, zone, hour, weekday, event_type, duration, occurred_at
                FROM activity_observations
                WHERE occurred_at >= ?
                ORDER BY occurred_at ASC
                """,
                (since,),
            ).fetchall()
        observations = [dict(row) for row in rows]
        by_person: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in observations:
            by_person[row["person_id"]].append(row)

        habits: list[dict[str, Any]] = []
        for person_id, records in by_person.items():
            arrivals = [r for r in records if r["event_type"] in {"appeared", "entered_zone"}]
            hour_counts = Counter(r["hour"] for r in arrivals)
            zone_counts = Counter(r["zone"] for r in records if r.get("zone"))
            weekday_counts = Counter(r["weekday"] for r in arrivals)
            sample_count = len(arrivals)
            if sample_count < minimum_samples:
                continue
            strongest = hour_counts.most_common(1)[0] if hour_counts else (None, 0)
            confidence = round(strongest[1] / sample_count, 3) if sample_count else 0.0
            habits.append({
                "person_id": person_id,
                "sample_count": sample_count,
                "typical_arrival_hour": strongest[0],
                "top_zone": zone_counts.most_common(1)[0][0] if zone_counts else None,
                "most_active_weekday": weekday_counts.most_common(1)[0][0] if weekday_counts else None,
                "confidence": confidence,
                "status": "learned" if confidence >= 0.5 else "learning",
            })
        habits.sort(key=lambda item: (item["confidence"], item["sample_count"]), reverse=True)
        return {"days": days, "count": len(habits), "habits": habits}

    def reminder_suggestions(self, days: int = 30) -> dict[str, Any]:
        habits = self.habits(days=days, minimum_samples=2)["habits"]
        suggestions: list[dict[str, Any]] = []
        for habit in habits:
            score = min(1.0, 0.35 + habit["confidence"] * 0.45 + min(habit["sample_count"], 20) / 100)
            hour = habit.get("typical_arrival_hour")
            zone = habit.get("top_zone")
            person_id = habit["person_id"]
            suggestions.append({
                "person_id": person_id,
                "trigger": "entered_zone" if zone else "appeared",
                "zone": zone,
                "suggested_hour": hour,
                "priority_score": round(score, 3),
                "reason": (
                    f"Person {person_id} repeatedly appears"
                    + (f" in {zone}" if zone else "")
                    + (f" around {hour:02d}:00" if hour is not None else "")
                    + f" ({habit['sample_count']} samples)."
                ),
                "recommended_rule": {
                    "name": f"Smart reminder for person {person_id}",
                    "trigger": "entered_zone" if zone else "appeared",
                    "zone": zone,
                    "message": "Assalamu Alaikum. This is your NoorBrain reminder.",
                    "cooldown_seconds": 1800,
                    "speak": True,
                    "enabled": False,
                },
                "automatic_action_taken": False,
            })
        return {"days": days, "count": len(suggestions), "suggestions": suggestions}

    def daily_summary(self, date: str | None = None) -> dict[str, Any]:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        timeline = self.timeline(date=date, limit=1000)["events"]
        people = sorted({event["person_id"] for event in timeline})
        zones = Counter(event["zone"] for event in timeline if event.get("zone"))
        event_types = Counter(event["event_type"] for event in timeline)
        return {
            "date": date,
            "event_count": len(timeline),
            "people_count": len(people),
            "people": people,
            "top_zone": zones.most_common(1)[0][0] if zones else None,
            "zone_counts": dict(zones),
            "event_counts": dict(event_types),
            "first_event_at": timeline[-1]["occurred_at"] if timeline else None,
            "last_event_at": timeline[0]["occurred_at"] if timeline else None,
        }

    def clear(self) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute("DELETE FROM activity_observations")
            return int(cursor.rowcount)


sprint7_intelligence = Sprint7Intelligence()
