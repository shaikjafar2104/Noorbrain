"""Persistent report snapshots stored alongside learning data."""
from __future__ import annotations
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "learning.db"

class ReportStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def initialize(self) -> None:
        with self._lock, self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS report_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT NOT NULL,
                    person_id TEXT,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_report_snapshots_type
                    ON report_snapshots(report_type, generated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_report_snapshots_person
                    ON report_snapshots(person_id, generated_at DESC);
            """)

    def save(self, report: Dict[str, Any]) -> int:
        window = report.get("window", {})
        generated_at = str(report.get("generated_at") or datetime.now(timezone.utc).isoformat())
        payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"), default=str)
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO report_snapshots
                   (report_type, person_id, period_start, period_end, generated_at, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    str(report.get("report_type", "unknown")),
                    report.get("person_id"),
                    str(window.get("start_at", "")),
                    str(window.get("end_at", "")),
                    generated_at,
                    payload,
                ),
            )
            return int(cursor.lastrowid)

    def latest(self, report_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        query = "SELECT * FROM report_snapshots"
        values: list[Any] = []
        if report_type:
            query += " WHERE report_type = ?"
            values.append(report_type)
        query += " ORDER BY generated_at DESC, id DESC LIMIT ?"
        values.append(max(1, min(100, int(limit))))
        with self.connect() as connection:
            rows = connection.execute(query, values).fetchall()
        output = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                payload = {}
            output.append({"id": row["id"], "report_type": row["report_type"], "generated_at": row["generated_at"], "report": payload})
        return output

    def integrity_check(self) -> str:
        with self.connect() as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0] if row else "unknown")

_store: Optional[ReportStore] = None
_lock = threading.Lock()
def get_report_store() -> ReportStore:
    global _store
    if _store is None:
        with _lock:
            if _store is None:
                _store = ReportStore()
    return _store
