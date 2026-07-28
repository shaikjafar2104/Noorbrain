from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database_path),
            timeout=30,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    person_id TEXT,
                    zone TEXT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5,
                    source TEXT NOT NULL DEFAULT 'manual',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL
                );

                CREATE INDEX IF NOT EXISTS idx_memories_created_at
                ON memories(created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_memories_person_id
                ON memories(person_id);

                CREATE INDEX IF NOT EXISTS idx_memories_kind
                ON memories(kind);

                CREATE INDEX IF NOT EXISTS idx_memories_zone
                ON memories(zone);
                """
            )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        try:
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        except json.JSONDecodeError:
            item["metadata"] = {}
        return item

    def add(
        self,
        *,
        kind: str,
        title: str,
        content: str,
        person_id: str | None = None,
        zone: str | None = None,
        importance: float = 0.5,
        source: str = "manual",
        metadata: dict[str, Any] | None = None,
        expires_at: float | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        memory_id = str(uuid.uuid4())
        importance = max(0.0, min(1.0, float(importance)))
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    memory_id, kind, person_id, zone, title, content,
                    importance, source, metadata_json, created_at,
                    updated_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    kind.strip(),
                    person_id,
                    zone,
                    title.strip(),
                    content.strip(),
                    importance,
                    source.strip() or "manual",
                    metadata_json,
                    now,
                    now,
                    expires_at,
                ),
            )

        return self.get(memory_id)

    def get(self, memory_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM memories WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()

        if row is None:
            raise KeyError(memory_id)
        return self._row_to_dict(row)

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        kind: str | None = None,
        person_id: str | None = None,
        zone: str | None = None,
        query: str | None = None,
        include_expired: bool = False,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []

        if kind:
            clauses.append("kind = ?")
            values.append(kind)
        if person_id:
            clauses.append("person_id = ?")
            values.append(person_id)
        if zone:
            clauses.append("zone = ?")
            values.append(zone)
        if query:
            clauses.append("(title LIKE ? OR content LIKE ?)")
            token = f"%{query}%"
            values.extend([token, token])
        if not include_expired:
            clauses.append("(expires_at IS NULL OR expires_at > ?)")
            values.append(time.time())

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        values.extend([max(1, min(int(limit), 500)), max(0, int(offset))])

        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memories
                {where}
                ORDER BY importance DESC, created_at DESC
                LIMIT ? OFFSET ?
                """,
                values,
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def delete(self, memory_id: str) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE memory_id = ?",
                (memory_id,),
            )
        return cursor.rowcount > 0

    def clear_expired(self) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (time.time(),),
            )
        return cursor.rowcount

    def stats(self) -> dict[str, Any]:
        now = time.time()
        with self._lock, self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM memories"
            ).fetchone()[0]
            active = connection.execute(
                """
                SELECT COUNT(*) FROM memories
                WHERE expires_at IS NULL OR expires_at > ?
                """,
                (now,),
            ).fetchone()[0]
            kinds = connection.execute(
                """
                SELECT kind, COUNT(*) AS count
                FROM memories
                GROUP BY kind
                ORDER BY count DESC
                """
            ).fetchall()
            people = connection.execute(
                """
                SELECT COUNT(DISTINCT person_id)
                FROM memories
                WHERE person_id IS NOT NULL AND person_id != ''
                """
            ).fetchone()[0]

        return {
            "total": total,
            "active": active,
            "expired": total - active,
            "people": people,
            "kinds": {row["kind"]: row["count"] for row in kinds},
            "database": str(self.database_path),
        }

    def context(
        self,
        *,
        person_id: str | None = None,
        zone: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        memories = self.list(
            person_id=person_id,
            zone=zone,
            limit=limit,
        )
        lines = []
        for item in memories:
            scope = []
            if item.get("person_id"):
                scope.append(f"person={item['person_id']}")
            if item.get("zone"):
                scope.append(f"zone={item['zone']}")
            prefix = f" ({', '.join(scope)})" if scope else ""
            lines.append(f"- [{item['kind']}] {item['title']}{prefix}: {item['content']}")

        return {
            "person_id": person_id,
            "zone": zone,
            "memory_count": len(memories),
            "memories": memories,
            "text": "\n".join(lines),
        }
