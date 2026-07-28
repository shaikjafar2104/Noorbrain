"""SQLite persistence for Sprint 9.1 Packs 1-3."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "learning.db"


class LearningStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path), timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._lock, self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    room TEXT,
                    person_id TEXT,
                    value REAL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    occurred_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_learning_events_occurred_at
                    ON learning_events(occurred_at);
                CREATE INDEX IF NOT EXISTS idx_learning_events_type
                    ON learning_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_learning_events_room
                    ON learning_events(room);
                CREATE INDEX IF NOT EXISTS idx_learning_events_person
                    ON learning_events(person_id);
                """
            )

    @staticmethod
    def _utc_iso(value: Optional[datetime] = None) -> str:
        moment = value or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Dict[str, Any]:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": row["id"],
            "event_type": row["event_type"],
            "source": row["source"],
            "room": row["room"],
            "person_id": row["person_id"],
            "value": row["value"],
            "metadata": metadata,
            "occurred_at": row["occurred_at"],
            "created_at": row["created_at"],
        }

    def add_event(
        self,
        *,
        event_type: str,
        source: str = "manual",
        room: Optional[str] = None,
        person_id: Optional[str] = None,
        value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        occurred = self._utc_iso(occurred_at)
        created = self._utc_iso()
        metadata_json = json.dumps(metadata or {}, separators=(",", ":"), ensure_ascii=False)
        with self._lock, self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO learning_events
                    (event_type, source, room, person_id, value, metadata_json, occurred_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_type, source, room, person_id, value, metadata_json, occurred, created),
            )
            row = connection.execute(
                "SELECT * FROM learning_events WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        if row is None:
            raise RuntimeError("Learning event was not saved")
        return self._row_to_event(row)

    def list_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        room: Optional[str] = None,
        person_id: Optional[str] = None,
        start_at: Optional[str] = None,
        end_at: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        values: List[Any] = []
        filters = {
            "event_type": event_type,
            "room": room,
            "person_id": person_id,
        }
        for column, value in filters.items():
            if value:
                conditions.append(f"{column} = ?")
                values.append(value)
        if start_at:
            conditions.append("occurred_at >= ?")
            values.append(start_at)
        if end_at:
            conditions.append("occurred_at <= ?")
            values.append(end_at)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"SELECT * FROM learning_events{where} ORDER BY occurred_at DESC, id DESC LIMIT ? OFFSET ?"
        values.extend([limit, offset])
        with self.connection() as connection:
            rows = connection.execute(query, values).fetchall()
        return [self._row_to_event(row) for row in rows]

    def count_events(self, *, start_at: Optional[str] = None, end_at: Optional[str] = None) -> int:
        conditions: List[str] = []
        values: List[Any] = []
        if start_at:
            conditions.append("occurred_at >= ?")
            values.append(start_at)
        if end_at:
            conditions.append("occurred_at <= ?")
            values.append(end_at)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self.connection() as connection:
            row = connection.execute(f"SELECT COUNT(*) AS count FROM learning_events{where}", values).fetchone()
        return int(row["count"] if row else 0)

    def aggregate(self, query: str, values: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(query, tuple(values)).fetchall()
        return [dict(row) for row in rows]

    def integrity_check(self) -> str:
        with self.connection() as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0] if row else "unknown")


_store: Optional[LearningStore] = None
_store_lock = threading.Lock()


def get_store() -> LearningStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = LearningStore()
    return _store
