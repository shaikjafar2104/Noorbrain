from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class HabitStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "habit_learning.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        if not self.path.exists():
            self.write({
                "schema_version": 1,
                "observations": [],
                "patterns": [],
                "suggestions": [],
            })

    def read(self) -> dict[str, Any]:
        with self.lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("observations", [])
        data.setdefault("patterns", [])
        data.setdefault("suggestions", [])
        return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            fd, tmp = tempfile.mkstemp(
                prefix="habit-learning-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def add(self, collection: str, item: dict[str, Any], limit: int = 5000) -> dict[str, Any]:
        data = self.read()
        record = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            **item,
        }
        data[collection].append(record)
        data[collection] = data[collection][-limit:]
        self.write(data)
        return record

    def list(self, collection: str, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self.read()[collection]))[:limit]

    def replace_patterns(self, patterns: list[dict[str, Any]]) -> None:
        data = self.read()
        data["patterns"] = patterns
        self.write(data)

    def summary(self) -> dict[str, Any]:
        data = self.read()
        return {
            "status": "ok",
            "observation_count": len(data["observations"]),
            "pattern_count": len(data["patterns"]),
            "suggestion_count": len(data["suggestions"]),
        }

habit_store = HabitStore()
