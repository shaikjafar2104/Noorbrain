from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HALOBrainStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "halo_brain.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({
                "schema_version": 1,
                "memories": [],
                "decisions": [],
                "executions": [],
                "signals": [],
            })

    def _read(self) -> dict[str, Any]:
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))

        payload.setdefault("schema_version", 1)
        payload.setdefault("memories", [])
        payload.setdefault("decisions", [])
        payload.setdefault("executions", [])
        payload.setdefault("signals", [])
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="halo-brain-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def add(self, collection: str, item: dict[str, Any], limit: int = 5000) -> dict[str, Any]:
        payload = self._read()
        record = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            **item,
        }
        payload[collection].append(record)
        payload[collection] = payload[collection][-limit:]
        self._write(payload)
        return record

    def list(self, collection: str, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self._read()[collection]))[:limit]

    def clear(self, collection: str) -> int:
        payload = self._read()
        removed = len(payload[collection])
        payload[collection] = []
        self._write(payload)
        return removed

    def summary(self) -> dict[str, Any]:
        payload = self._read()
        return {
            "status": "ok",
            "memory_count": len(payload["memories"]),
            "decision_count": len(payload["decisions"]),
            "execution_count": len(payload["executions"]),
            "signal_count": len(payload["signals"]),
        }


halo_brain_store = HALOBrainStore()
