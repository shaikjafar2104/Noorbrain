"""
Human Activity Intelligence — SQLite-backed activity store.

Uses a SEPARATE activity DB so the existing noorbrain.db is never touched,
deleted, or rewritten.

Add only the schema needed for:
  ActivityEvent, ActivitySession, ActivitySettings,
  LearnedPattern, RuleSuggestion, ActivitySnapshot

Backward-compatible migrations. Snapshots OFF by default.

Testability: ActivityStore(db_path=tmp_path) for injected test paths.
Production singleton continues using data/human_activity_intelligence.db.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "human_activity_intelligence.db"


class SessionState:
    """In-memory session descriptor, persisted via activity_store."""

    def __init__(
        self,
        *,
        session_id: str,
        person_id: str,
        track_id: str | None = None,
        activity_type: str = "unknown",
        zone: str = "",
        room: str = "",
        started_at: float = 0.0,
        started_at_iso: str = "",
        confidence: float = 0.5,
        event_count: int = 0,
        support_signals: list[str] | None = None,
        last_observed_at: float = 0.0,
        last_observed_iso: str = "",
    ) -> None:
        self.session_id = session_id
        self.person_id = person_id
        self.track_id = track_id
        self.activity_type = activity_type
        self.zone = zone
        self.room = room
        self.started_at = started_at
        self.started_at_iso = started_at_iso
        self.confidence = confidence
        self.event_count = event_count
        self.support_signals = support_signals or []
        self.last_observed_at = last_observed_at
        self.last_observed_iso = last_observed_iso
        self.ended_at: float | None = None
        self.ended_at_iso: str | None = None
        self.duration_seconds: float | None = None
        self.motion_duration: float = 0.0
        self.stationary_duration: float = 0.0
        self.motion_started_at: float = started_at
        self.stationary_started_at: float = started_at
        self.last_motion_state: str = "stationary"

    @property
    def ended_at_set(self) -> bool:
        return self.ended_at is not None


class ActivityStore:
    """Bounded persistent store backed by a separate SQLite DB.

    Testability: pass db_path= to use a temporary DB. Production uses
    the default data/human_activity_intelligence.db.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._ensure_tables()

    # ------------------------------------------------------------------
    # connection / lifecycle
    # ------------------------------------------------------------------

    def _ensure_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path), timeout=10.0)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    @property
    def db_path(self) -> Path:
        return self._db_path

    # ------------------------------------------------------------------
    # schema + migrations
    # ------------------------------------------------------------------

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(str(self._db_path), timeout=10.0)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at_epoch REAL NOT NULL,
                    created_at_iso TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    person_id TEXT,
                    track_id TEXT,
                    zone TEXT,
                    room TEXT,
                    session_id TEXT,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    duration_seconds REAL,
                    metadata TEXT,
                    previous_zone TEXT,
                    previous_room TEXT
                );

                CREATE TABLE IF NOT EXISTS activity_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    person_id TEXT,
                    track_id TEXT,
                    activity_type TEXT NOT NULL,
                    zone TEXT,
                    room TEXT,
                    started_at_epoch REAL NOT NULL,
                    started_at_iso TEXT NOT NULL,
                    ended_at_epoch REAL,
                    ended_at_iso TEXT,
                    duration_seconds REAL,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    peak_confidence REAL,
                    support_signals TEXT,
                    last_observed_at_epoch REAL,
                    last_observed_iso TEXT,
                    event_count INTEGER NOT NULL DEFAULT 0,
                    ENDED INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS activity_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at_iso TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS learned_patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    person_id TEXT,
                    zone TEXT,
                    room TEXT,
                    activity_type TEXT,
                    usual_start_hour INTEGER,
                    usual_end_hour INTEGER,
                    usual_days TEXT,
                    support_count INTEGER NOT NULL DEFAULT 0,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    description TEXT,
                    first_seen_iso TEXT,
                    last_seen_iso TEXT,
                    updated_at_iso TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rule_suggestions (
                    id TEXT PRIMARY KEY,
                    suggestion_type TEXT NOT NULL,
                    pattern_id TEXT,
                    rule_name TEXT,
                    rule_trigger TEXT,
                    rule_zone TEXT,
                    rule_message TEXT,
                    rule_action_type TEXT,
                    rule_target_node TEXT,
                    rule_cooldown_seconds INTEGER,
                    rule_days TEXT,
                    priority REAL NOT NULL DEFAULT 0.5,
                    status TEXT NOT NULL DEFAULT 'new',
                    dismissed_at_iso TEXT,
                    snoozed_until_epoch REAL,
                    never_suggest INTEGER NOT NULL DEFAULT 0,
                    user_approved INTEGER NOT NULL DEFAULT 0,
                    created_at_iso TEXT NOT NULL,
                    updated_at_iso TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_json TEXT NOT NULL,
                    created_at_epoch REAL NOT NULL,
                    created_at_iso TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS habits (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    target_days TEXT DEFAULT '["mon","tue","wed","thu","fri","sat","sun"]',
                    trigger_type TEXT,
                    trigger_value TEXT,
                    created_at_iso TEXT NOT NULL,
                    last_completed_iso TEXT,
                    streak_current INTEGER DEFAULT 0,
                    streak_longest INTEGER DEFAULT 0,
                    completions_json TEXT DEFAULT '[]'
                );

                CREATE INDEX IF NOT EXISTS idx_ae_type ON activity_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_ae_person ON activity_events(person_id);
                CREATE INDEX IF NOT EXISTS idx_ae_session ON activity_events(session_id);
                CREATE INDEX IF NOT EXISTS idx_ae_created ON activity_events(created_at_epoch);
                CREATE INDEX IF NOT EXISTS idx_as_session ON activity_sessions(session_id);
                CREATE INDEX IF NOT EXISTS idx_as_person ON activity_sessions(person_id);
                CREATE INDEX IF NOT EXISTS idx_rp_person ON learned_patterns(person_id);
                CREATE INDEX IF NOT EXISTS idx_rs_status ON rule_suggestions(status);
                """
            )
            self._migrate(conn)
        finally:
            conn.close()

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        cur = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
        current = int(cur.fetchone()[0])
        if current >= 1:
            # Check if we need to add trigger columns (migration)
            cols = conn.execute("PRAGMA table_info(habits)").fetchall()
            col_names = [c[1] for c in cols]
            if "trigger_type" not in col_names:
                conn.execute("ALTER TABLE habits ADD COLUMN trigger_type TEXT")
                conn.execute("ALTER TABLE habits ADD COLUMN trigger_value TEXT")
                conn.commit()
            return
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (1, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    # ------------------------------------------------------------------
    # settings
    # ------------------------------------------------------------------

    def get_setting(self, key: str) -> str | None:
        with self._lock:
            conn = self._ensure_connection()
            row = conn.execute(
                "SELECT value FROM activity_settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> dict[str, Any]:
        with self._lock:
            conn = self._ensure_connection()
            conn.execute(
                "INSERT OR REPLACE INTO activity_settings (key, value, updated_at_iso) VALUES (?, ?, ?)",
                (key, value, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return {"key": key, "value": value}

    def get_all_settings(self) -> dict[str, str]:
        with self._lock:
            conn = self._ensure_connection()
            rows = conn.execute("SELECT key, value FROM activity_settings").fetchall()
            return {r["key"]: r["value"] for r in rows}

    # ------------------------------------------------------------------
    # activity events
    # ------------------------------------------------------------------

    def add_event(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            conn = self._ensure_connection()
            now = time.time()
            row = conn.execute(
                """
                INSERT INTO activity_events (
                    created_at_epoch, created_at_iso, event_type,
                    person_id, track_id, zone, room, session_id,
                    confidence, duration_seconds, metadata,
                    previous_zone, previous_room
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                    str(event.get("event_type") or "unknown"),
                    event.get("person_id"),
                    event.get("track_id"),
                    event.get("zone"),
                    event.get("room"),
                    event.get("session_id"),
                    float(event.get("confidence", 0.5)),
                    event.get("duration_seconds"),
                    json.dumps(event.get("metadata") or {}),
                    event.get("previous_zone"),
                    event.get("previous_room"),
                ),
            )
            conn.commit()
            return {
                "id": row.lastrowid,
                "created_at_epoch": now,
                "created_at_iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                **event,
            }

    def list_events(
        self,
        *,
        event_type: str | None = None,
        person_id: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._ensure_connection()
            clauses: list[str] = []
            params: list[Any] = []
            if event_type:
                clauses.append("event_type = ?")
                params.append(event_type)
            if person_id:
                clauses.append("person_id = ?")
                params.append(person_id)
            if session_id:
                clauses.append("session_id = ?")
                params.append(session_id)
            where = " AND ".join(clauses) if clauses else "1=1"
            rows = conn.execute(
                f"SELECT * FROM activity_events WHERE {where} ORDER BY created_at_epoch DESC LIMIT ? OFFSET ?",
                params + [int(limit), int(offset)],
            )
            return [self._event_row_to_dict(r) for r in rows]

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.list_events(limit=limit)

    @staticmethod
    def _event_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "created_at_epoch": row["created_at_epoch"],
            "created_at_iso": row["created_at_iso"],
            "event_type": row["event_type"],
            "person_id": row["person_id"],
            "track_id": row["track_id"],
            "zone": row["zone"],
            "room": row["room"],
            "session_id": row["session_id"],
            "confidence": row["confidence"],
            "duration_seconds": row["duration_seconds"],
            "metadata": json.loads(row["metadata"] or "{}"),
            "previous_zone": row["previous_zone"],
            "previous_room": row["previous_room"],
        }

    def event_count(self) -> int:
        with self._lock:
            conn = self._ensure_connection()
            return int(conn.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0])

    def count_events(self, event_type: str) -> int:
        """Count events of a specific event_type (for dashboard summaries)."""
        with self._lock:
            conn = self._ensure_connection()
            return int(conn.execute(
                "SELECT COUNT(*) FROM activity_events WHERE event_type = ?",
                (str(event_type),),
            ).fetchone()[0])

    # ------------------------------------------------------------------
    # activity sessions
    # ------------------------------------------------------------------

    def upsert_session(self, session: SessionState) -> dict[str, Any]:
        with self._lock:
            conn = self._ensure_connection()
            now = time.time()
            existing = conn.execute(
                "SELECT * FROM activity_sessions WHERE session_id = ?", (session.session_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE activity_sessions SET
                        last_observed_at_epoch = ?,
                        last_observed_iso = ?,
                        confidence = ?,
                        peak_confidence = MAX(peak_confidence, ?),
                        event_count = event_count + 1,
                        zone = COALESCE(?, zone),
                        room = COALESCE(?, room),
                        activity_type = COALESCE(?, activity_type)
                    WHERE session_id = ?
                    """,
                    (
                        now,
                        datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                        session.confidence,
                        session.confidence,
                        session.zone or None,
                        session.room or None,
                        session.activity_type or None,
                        session.session_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO activity_sessions (
                        session_id, person_id, track_id, activity_type,
                        zone, room, started_at_epoch, started_at_iso,
                        confidence, support_signals, last_observed_at_epoch,
                        last_observed_iso, event_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        session.session_id,
                        session.person_id,
                        session.track_id,
                        session.activity_type,
                        session.zone,
                        session.room,
                        session.started_at,
                        session.started_at_iso,
                        session.confidence,
                        json.dumps(session.support_signals),
                        session.started_at,
                        session.started_at_iso,
                    ),
                )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM activity_sessions WHERE session_id = ?", (session.session_id,)
            ).fetchone()
            return self._session_row_to_dict(row)

    def end_session(self, session_id: str, confidence: float = 0.5) -> dict[str, Any] | None:
        with self._lock:
            conn = self._ensure_connection()
            now = time.time()
            conn.execute(
                """
                UPDATE activity_sessions SET
                    ended_at_epoch = ?,
                    ended_at_iso = ?,
                    duration_seconds = ?,
                    confidence = ?,
                    ENDED = 1
                WHERE session_id = ?
                """,
                (
                    now,
                    datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                    now - float(conn.execute(
                        "SELECT started_at_epoch FROM activity_sessions WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()[0]),
                    confidence,
                    session_id,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM activity_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            return self._session_row_to_dict(row) if row else None

    def list_sessions(
        self,
        *,
        person_id: str | None = None,
        activity_type: str | None = None,
        active: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._ensure_connection()
            clauses: list[str] = []
            params: list[Any] = []
            if person_id:
                clauses.append("person_id = ?")
                params.append(person_id)
            if activity_type:
                clauses.append("activity_type = ?")
                params.append(activity_type)
            if active is not None:
                clauses.append("ENDED = ?")
                params.append(0 if active else 1)
            where = " AND ".join(clauses) if clauses else "1=1"
            rows = conn.execute(
                f"SELECT * FROM activity_sessions WHERE {where} ORDER BY started_at_epoch DESC LIMIT ?",
                params + [int(limit)],
            )
            return [self._session_row_to_dict(r) for r in rows]

    def active_sessions(self) -> list[dict[str, Any]]:
        return self.list_sessions(active=True, limit=200)

    def session_count(self) -> int:
        with self._lock:
            conn = self._ensure_connection()
            return int(conn.execute("SELECT COUNT(*) FROM activity_sessions").fetchone()[0])

    @staticmethod
    def _session_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "person_id": row["person_id"],
            "track_id": row["track_id"],
            "activity_type": row["activity_type"],
            "zone": row["zone"],
            "room": row["room"],
            "started_at_epoch": row["started_at_epoch"],
            "started_at_iso": row["started_at_iso"],
            "ended_at_epoch": row["ended_at_epoch"],
            "ended_at_iso": row["ended_at_iso"],
            "duration_seconds": row["duration_seconds"],
            "confidence": row["confidence"],
            "peak_confidence": row["peak_confidence"],
            "support_signals": json.loads(row["support_signals"] or "[]"),
            "last_observed_at_epoch": row["last_observed_at_epoch"],
            "last_observed_iso": row["last_observed_iso"],
            "event_count": row["event_count"],
            "ended": bool(row["ENDED"]),
        }

    # ------------------------------------------------------------------
    # learned patterns
    # ------------------------------------------------------------------

    def add_pattern(self, pattern: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            conn = self._ensure_connection()
            pid = str(pattern.get("id") or "").strip()
            if not pid:
                raise ValueError("pattern id required")
            now_iso = datetime.now(timezone.utc).isoformat()
            existing = conn.execute(
                "SELECT * FROM learned_patterns WHERE id = ?", (pid,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE learned_patterns SET
                        support_count = support_count + 1,
                        confidence = ?,
                        last_seen_iso = ?,
                        updated_at_iso = ?
                    WHERE id = ?
                    """,
                    (
                        float(pattern.get("confidence", 0.5)),
                        now_iso,
                        now_iso,
                        pid,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO learned_patterns (
                        id, pattern_type, person_id, zone, room,
                        activity_type, usual_start_hour, usual_end_hour,
                        usual_days, support_count, confidence,
                        description, first_seen_iso, last_seen_iso,
                        updated_at_iso
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid,
                        pattern.get("pattern_type") or "activity_pattern",
                        pattern.get("person_id"),
                        pattern.get("zone"),
                        pattern.get("room"),
                        pattern.get("activity_type"),
                        pattern.get("usual_start_hour"),
                        pattern.get("usual_end_hour"),
                        json.dumps(pattern.get("usual_days") or []),
                        int(pattern.get("support_count", 1)),
                        float(pattern.get("confidence", 0.5)),
                        pattern.get("description"),
                        pattern.get("first_seen_iso") or now_iso,
                        now_iso,
                        now_iso,
                    ),
                )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM learned_patterns WHERE id = ?", (pid,)
            ).fetchone()
            return self._pattern_row_to_dict(row)

    def list_patterns(
        self,
        *,
        person_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._ensure_connection()
            clauses: list[str] = []
            params: list[Any] = []
            if person_id:
                clauses.append("person_id = ?")
                params.append(person_id)
            where = " AND ".join(clauses) if clauses else "1=1"
            rows = conn.execute(
                f"SELECT * FROM learned_patterns WHERE {where} ORDER BY confidence DESC, support_count DESC LIMIT ?",
                params + [int(limit)],
            )
            return [self._pattern_row_to_dict(r) for r in rows]

    def pattern_count(self) -> int:
        with self._lock:
            conn = self._ensure_connection()
            return int(conn.execute("SELECT COUNT(*) FROM learned_patterns").fetchone()[0])

    @staticmethod
    def _pattern_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "pattern_type": row["pattern_type"],
            "person_id": row["person_id"],
            "zone": row["zone"],
            "room": row["room"],
            "activity_type": row["activity_type"],
            "usual_start_hour": row["usual_start_hour"],
            "usual_end_hour": row["usual_end_hour"],
            "usual_days": json.loads(row["usual_days"] or "[]"),
            "support_count": row["support_count"],
            "confidence": row["confidence"],
            "description": row["description"],
            "first_seen_iso": row["first_seen_iso"],
            "last_seen_iso": row["last_seen_iso"],
            "updated_at_iso": row["updated_at_iso"],
        }

    # ------------------------------------------------------------------
    # rule suggestions
    # ------------------------------------------------------------------

    def add_suggestion(self, suggestion: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            conn = self._ensure_connection()
            sid = str(suggestion.get("id") or "").strip()
            if not sid:
                raise ValueError("suggestion id required")
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO rule_suggestions (
                    id, suggestion_type, pattern_id, rule_name, rule_trigger,
                    rule_zone, rule_message, rule_action_type, rule_target_node,
                    rule_cooldown_seconds, rule_days, priority, status,
                    never_suggest, user_approved, created_at_iso, updated_at_iso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    suggestion.get("suggestion_type") or "rule_suggestion",
                    suggestion.get("pattern_id"),
                    suggestion.get("rule_name") or "",
                    suggestion.get("rule_trigger") or "",
                    suggestion.get("rule_zone") or "",
                    suggestion.get("rule_message") or "",
                    suggestion.get("rule_action_type") or "notification",
                    suggestion.get("rule_target_node") or "",
                    int(suggestion.get("rule_cooldown_seconds", 0)),
                    json.dumps(suggestion.get("rule_days") or []),
                    float(suggestion.get("priority", 0.5)),
                    str(suggestion.get("status", "new")),
                    int(bool(suggestion.get("never_suggest", False))),
                    int(bool(suggestion.get("user_approved", False))),
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM rule_suggestions WHERE id = ?", (sid,)
            ).fetchone()
            return self._suggestion_row_to_dict(row)

    def get_suggestion(self, sid: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._ensure_connection()
            row = conn.execute(
                "SELECT * FROM rule_suggestions WHERE id = ?", (sid,)
            ).fetchone()
            return self._suggestion_row_to_dict(row) if row else None

    def update_suggestion(self, sid: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            conn = self._ensure_connection()
            now_iso = datetime.now(timezone.utc).isoformat()
            set_clause: list[str] = ["updated_at_iso = ?"]
            params: list[Any] = [now_iso]
            if "status" in changes:
                set_clause.append("status = ?")
                params.append(str(changes["status"]))
            if "dismissed_at_iso" in changes:
                set_clause.append("dismissed_at_iso = ?")
                params.append(changes["dismissed_at_iso"])
            if "never_suggest" in changes:
                set_clause.append("never_suggest = ?")
                params.append(int(bool(changes["never_suggest"])))
            if "user_approved" in changes:
                set_clause.append("user_approved = ?")
                params.append(int(bool(changes["user_approved"])))
            if "snoozed_until_epoch" in changes:
                set_clause.append("snoozed_until_epoch = ?")
                params.append(float(changes["snoozed_until_epoch"]))
            params.append(sid)
            conn.execute(
                f"UPDATE rule_suggestions SET {', '.join(set_clause)} WHERE id = ?",
                params,
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM rule_suggestions WHERE id = ?", (sid,)
            ).fetchone()
            return self._suggestion_row_to_dict(row) if row else None

    def list_suggestions(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._ensure_connection()
            clauses: list[str] = []
            params: list[Any] = []
            if status:
                clauses.append("status = ?")
                params.append(status)
            where = " AND ".join(clauses) if clauses else "1=1"
            rows = conn.execute(
                f"SELECT * FROM rule_suggestions WHERE {where} ORDER BY priority DESC, created_at_iso DESC LIMIT ?",
                params + [int(limit)],
            )
            return [self._suggestion_row_to_dict(r) for r in rows]

    def dismiss_suggestion(self, sid: str) -> dict[str, Any] | None:
        return self.update_suggestion(sid, {"status": "dismissed", "dismissed_at_iso": datetime.now(timezone.utc).isoformat()})

    def snooze_suggestion(self, sid: str, minutes: int = 30) -> dict[str, Any] | None:
        return self.update_suggestion(sid, {"status": "snoozed", "snoozed_until_epoch": time.time() + int(minutes) * 60})

    def never_suggest(self, sid: str) -> dict[str, Any] | None:
        return self.update_suggestion(sid, {"status": "never_suggest", "never_suggest": True})

    def approve_suggestion(self, sid: str) -> dict[str, Any] | None:
        return self.update_suggestion(sid, {"status": "approved", "user_approved": True})

    def reject_suggestion(self, sid: str) -> dict[str, Any] | None:
        """Reject a suggestion and mark it as rejected for cooldown handling."""
        return self.update_suggestion(sid, {"status": "rejected", "user_approved": False})

    def suggestion_count(self) -> int:
        with self._lock:
            conn = self._ensure_connection()
            return int(conn.execute("SELECT COUNT(*) FROM rule_suggestions").fetchone()[0])

    @staticmethod
    def _suggestion_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "suggestion_type": row["suggestion_type"],
            "pattern_id": row["pattern_id"],
            "rule_name": row["rule_name"],
            "rule_trigger": row["rule_trigger"],
            "rule_zone": row["rule_zone"],
            "rule_message": row["rule_message"],
            "rule_action_type": row["rule_action_type"],
            "rule_target_node": row["rule_target_node"],
            "rule_cooldown_seconds": row["rule_cooldown_seconds"],
            "rule_days": json.loads(row["rule_days"] or "[]"),
            "priority": row["priority"],
            "status": row["status"],
            "dismissed_at_iso": row["dismissed_at_iso"],
            "snoozed_until_epoch": row["snoozed_until_epoch"],
            "never_suggest": bool(row["never_suggest"]),
            "user_approved": bool(row["user_approved"]),
            "created_at_iso": row["created_at_iso"],
            "updated_at_iso": row["updated_at_iso"],
        }

    # ------------------------------------------------------------------
    # snapshots
    # ------------------------------------------------------------------

    def save_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        enabled = self.get_setting("snapshot_enabled")
        if enabled is None or enabled.strip().lower() not in {"1", "true", "yes"}:
            return None
        with self._lock:
            conn = self._ensure_connection()
            now = time.time()
            conn.execute(
                "INSERT INTO activity_snapshots (snapshot_json, created_at_epoch, created_at_iso) VALUES (?, ?, ?)",
                (json.dumps(snapshot), now, datetime.fromtimestamp(now, tz=timezone.utc).isoformat()),
            )
            conn.commit()
            return {"saved": True, "created_at_iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat()}

    def list_snapshots(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._ensure_connection()
            rows = conn.execute(
                "SELECT id, snapshot_json, created_at_epoch, created_at_iso FROM activity_snapshots ORDER BY created_at_epoch DESC LIMIT ?",
                (int(limit),),
            )
            return [
                {
                    "id": r["id"],
                    "snapshot": json.loads(r["snapshot_json"]),
                    "created_at_epoch": r["created_at_epoch"],
                    "created_at_iso": r["created_at_iso"],
                }
                for r in rows
            ]

    def snapshot_count(self) -> int:
        with self._lock:
            conn = self._ensure_connection()
            return int(conn.execute("SELECT COUNT(*) FROM activity_snapshots").fetchone()[0])

    # ------------------------------------------------------------------
    # Habits — Islamic practice streak tracking
    # ------------------------------------------------------------------

    def list_habits(self) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._ensure_connection()
            rows = conn.execute(
                "SELECT * FROM habits ORDER BY category, name"
            ).fetchall()
            return [self._habit_row_to_dict(r) for r in rows]

    @staticmethod
    def _habit_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "target_days": json.loads(row["target_days"] or "[]"),
            "trigger_type": row["trigger_type"] if "trigger_type" in row.keys() else None,
            "trigger_value": row["trigger_value"] if "trigger_value" in row.keys() else None,
            "created_at_iso": row["created_at_iso"],
            "last_completed_iso": row["last_completed_iso"],
            "streak_current": row["streak_current"],
            "streak_longest": row["streak_longest"],
            "completions": json.loads(row["completions_json"] or "[]"),
        }

    def complete_habit(self, habit_id: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        with self._lock:
            conn = self._ensure_connection()
            row = conn.execute(
                "SELECT * FROM habits WHERE id = ?", (habit_id,)
            ).fetchone()
            if not row:
                return None

            streak_current = row["streak_current"]
            streak_longest = row["streak_longest"]
            last_completed_iso = row["last_completed_iso"]
            target_days = json.loads(row["target_days"] or "[]")

            # Islam-aware streak logic — use Hijri date if available
            # Falls back to Gregorian day-based logic if Hijri not available
            today = now.date().isoformat()
            completions = json.loads(row["completions_json"] or "[]")
            
            # Check if we need to reset streak (habit was missed)
            if last_completed_iso:
                try:
                    last_date = datetime.fromisoformat(last_completed_iso).date()
                    days_since = (now.date() - last_date).days
                    
                    # Check if yesterday's habit was supposed to be done
                    yesterday = (now - timedelta(days=1)).date()
                    yesterday_str = yesterday.isoformat()
                    day_of_week = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][yesterday.weekday()]
                    
                    if days_since > 1 and day_of_week in target_days:
                        # Missed yesterday — reset streak
                        new_streak = 0
                    elif days_since >= 1:
                        # Different day — increment streak
                        new_streak = streak_current + 1
                    else:
                        # Same day — don't increment, just update timestamp
                        new_streak = streak_current
                except Exception:
                    new_streak = streak_current + 1
            else:
                # First completion
                new_streak = 1

            new_longest = max(streak_longest, new_streak)
            completions.append(now_iso)

            conn.execute(
                """
                UPDATE habits SET
                    last_completed_iso = ?,
                    streak_current = ?,
                    streak_longest = ?,
                    completions_json = ?
                WHERE id = ?
                """,
                (now_iso, new_streak, new_longest, json.dumps(completions), habit_id)
            )
            conn.commit()

            updated = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
            return self._habit_row_to_dict(updated)

    def reset_habit_streak(self, habit_id: str) -> dict[str, Any] | None:
        with self._lock:
            conn = self._ensure_connection()
            row = conn.execute(
                "SELECT * FROM habits WHERE id = ?", (habit_id,)
            ).fetchone()
            if not row:
                return None

            conn.execute(
                "UPDATE habits SET streak_current = 0 WHERE id = ?", (habit_id,)
            )
            conn.commit()

            updated = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
            return self._habit_row_to_dict(updated)

    def delete_habit(self, habit_id: str) -> bool:
        """Delete a habit. Returns True if deleted, False if not found."""
        with self._lock:
            conn = self._ensure_connection()
            cur = conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
            conn.commit()
            return cur.rowcount > 0

    def upsert_habit(self, habit: dict[str, Any]) -> dict[str, Any]:
        habit_id = str(habit.get("id") or "").strip()
        if not habit_id:
            raise ValueError("habit id required")
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._ensure_connection()
            existing = conn.execute(
                "SELECT * FROM habits WHERE id = ?", (habit_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE habits SET
                        name = ?, category = ?, target_days = ?,
                        trigger_type = ?, trigger_value = ?
                    WHERE id = ?
                    """,
                    (
                        habit.get("name", existing["name"]),
                        habit.get("category", existing["category"]),
                        json.dumps(habit.get("target_days", ["mon","tue","wed","thu","fri","sat","sun"])),
                        habit.get("trigger_type"),
                        habit.get("trigger_value"),
                        habit_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO habits (
                        id, name, category, target_days, trigger_type, trigger_value,
                        created_at_iso
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        habit_id,
                        habit.get("name", ""),
                        habit.get("category", ""),
                        json.dumps(habit.get("target_days", ["mon","tue","wed","thu","fri","sat","sun"])),
                        habit.get("trigger_type"),
                        habit.get("trigger_value"),
                        habit.get("created_at_iso") or now_iso,
                    ),
                )
            conn.commit()
            row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
            return self._habit_row_to_dict(row)

    def check_habit_trigger(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Check if a HAI event should auto-complete a habit."""
        event_type = event.get("event_type", "")
        zone = event.get("zone", "")
        room = event.get("room", "")
        activity_type = event.get("activity_type", "") or event.get("metadata", {}).get("activity_type", "")
        triggered: list[dict[str, Any]] = []

        with self._lock:
            conn = self._ensure_connection()
            rows = conn.execute(
                "SELECT * FROM habits WHERE trigger_type IS NOT NULL"
            ).fetchall()
            for row in rows:
                t_type = row["trigger_type"]
                t_val = row["trigger_value"]
                should_complete = False

                if t_type == "event_type" and event_type == t_val:
                    should_complete = True
                elif t_type == "zone" and zone == t_val:
                    should_complete = True
                elif t_type == "zone_activity" and zone == t_val and activity_type == "stationary":
                    should_complete = True
                elif t_type == "activity" and activity_type == t_val:
                    should_complete = True

                if should_complete:
                    completed = self.complete_habit(row["id"])
                    if completed:
                        triggered.append(completed)

        return triggered


# Production singleton uses the default DB path.
activity_store = ActivityStore()


def migrate() -> dict[str, Any]:
    """Run migrations (idempotent). Return current schema version."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
        return {"version": int(cur.fetchone()[0]), "status": "ok"}
    finally:
        conn.close()


# initialize DB on import
migrate()
