from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ContextManager:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "voice.db"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS voice_context (
                context_key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                person_id TEXT,
                room TEXT,
                updated_at TEXT NOT NULL
            )""")

    def set(self, key: str, value: Any, person_id: Optional[str] = None, room: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("""INSERT INTO voice_context(context_key,value_json,person_id,room,updated_at)
                VALUES(?,?,?,?,?) ON CONFLICT(context_key) DO UPDATE SET
                value_json=excluded.value_json, person_id=excluded.person_id,
                room=excluded.room, updated_at=excluded.updated_at""",
                (key, json.dumps(value), person_id, room, now))
        return {"status": "ok", "key": key, "value": value, "updated_at": now}

    def get(self, key: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM voice_context WHERE context_key=?", (key,)).fetchone()
        if not row:
            return {"status": "not_found", "key": key}
        return {"status": "ok", "key": key, "value": json.loads(row["value_json"]),
                "person_id": row["person_id"], "room": row["room"], "updated_at": row["updated_at"]}

    def snapshot(self, limit: int = 100) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM voice_context ORDER BY updated_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
        items = [{"key": r["context_key"], "value": json.loads(r["value_json"]), "person_id": r["person_id"],
                  "room": r["room"], "updated_at": r["updated_at"]} for r in rows]
        return {"status": "ok", "count": len(items), "items": items}
