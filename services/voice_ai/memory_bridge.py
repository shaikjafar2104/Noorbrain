from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional


class MemoryBridge:
    """Read-only bridge to NoorBrain learning history. It degrades safely when unavailable."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.db_path = self.project_root / "data" / "learning.db"

    def status(self) -> Dict[str, Any]:
        return {"available": self.db_path.is_file(), "database": str(self.db_path)}

    def recent_events(self, person_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        if not self.db_path.is_file():
            return {"status": "unavailable", "events": [], "reason": "learning database not found"}
        limit = max(1, min(limit, 100))
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                table = "learning_events" if "learning_events" in tables else ("events" if "events" in tables else None)
                if not table:
                    return {"status": "unavailable", "events": [], "reason": "event table not found"}
                columns = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
                where, params = "", []
                if person_id and "person_id" in columns:
                    where, params = " WHERE person_id=?", [person_id]
                order_col = "created_at" if "created_at" in columns else ("timestamp" if "timestamp" in columns else "rowid")
                rows = conn.execute(f"SELECT * FROM {table}{where} ORDER BY {order_col} DESC LIMIT ?", (*params, limit)).fetchall()
            return {"status": "ok", "events": [dict(r) for r in rows], "count": len(rows)}
        except Exception as exc:
            return {"status": "unavailable", "events": [], "reason": str(exc)}
