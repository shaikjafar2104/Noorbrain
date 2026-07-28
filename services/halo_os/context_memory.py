from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContextMemory:
    def __init__(self, path: Path | None = None) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = path or project / "data" / "halo_context_memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({
                "schema_version": 1,
                "sessions": {},
            })

    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(f"HALO context memory is unreadable: {exc}") from exc

            if not isinstance(payload, dict):
                raise RuntimeError("HALO context memory root must be an object.")

            payload.setdefault("schema_version", 1)
            payload.setdefault("sessions", {})
            return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="halo-context-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(
                        payload,
                        handle,
                        indent=2,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def get(self, session_id: str) -> dict[str, Any]:
        payload = self._read()
        session = payload["sessions"].get(session_id)

        if not isinstance(session, dict):
            return {
                "session_id": session_id,
                "context": {},
                "updated_at": None,
            }

        return {
            "session_id": session_id,
            "context": dict(session.get("context") or {}),
            "updated_at": session.get("updated_at"),
        }

    def update(
        self,
        session_id: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._read()
        sessions = payload["sessions"]
        current = sessions.get(session_id)

        if not isinstance(current, dict):
            current = {"context": {}}

        context = dict(current.get("context") or {})
        context.update(values)

        sessions[session_id] = {
            "context": context,
            "updated_at": utc_now(),
        }

        self._write(payload)
        return self.get(session_id)

    def replace(
        self,
        session_id: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._read()
        payload["sessions"][session_id] = {
            "context": dict(values),
            "updated_at": utc_now(),
        }
        self._write(payload)
        return self.get(session_id)

    def clear(self, session_id: str) -> int:
        payload = self._read()
        existed = session_id in payload["sessions"]
        payload["sessions"].pop(session_id, None)
        self._write(payload)
        return 1 if existed else 0

    def list_sessions(self) -> list[dict[str, Any]]:
        payload = self._read()
        items = []

        for session_id, session in payload["sessions"].items():
            if not isinstance(session, dict):
                continue
            items.append({
                "session_id": session_id,
                "keys": sorted((session.get("context") or {}).keys()),
                "updated_at": session.get("updated_at"),
            })

        items.sort(
            key=lambda item: item.get("updated_at") or "",
            reverse=True,
        )
        return items


context_memory = ContextMemory()
