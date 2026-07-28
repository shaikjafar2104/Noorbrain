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


class FamilyProfileStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "sprint12_family_profiles.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        if not self.path.exists():
            self._write({"schema_version": 1, "members": []})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="family-",
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

    def list(self) -> list[dict[str, Any]]:
        return list(self._read().get("members", []))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Member name is required.")

        now = utc_now()
        member = {
            "id": uuid4().hex,
            "name": name,
            "role": str(payload.get("role") or "member"),
            "language": str(payload.get("language") or "en"),
            "permissions": list(payload.get("permissions") or []),
            "preferences": dict(payload.get("preferences") or {}),
            "presence": {
                "status": "unknown",
                "room": None,
                "updated_at": None,
            },
            "created_at": now,
            "updated_at": now,
        }

        items = self.list()
        items.append(member)
        self._write({"schema_version": 1, "members": items})
        return member

    def get(self, member_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list() if item["id"] == member_id), None)

    def update(self, member_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        items = self.list()
        index = next((i for i, item in enumerate(items) if item["id"] == member_id), None)
        if index is None:
            raise KeyError(f"Member not found: {member_id}")

        for key, value in patch.items():
            if key not in {"id", "created_at", "presence"}:
                items[index][key] = value

        items[index]["updated_at"] = utc_now()
        self._write({"schema_version": 1, "members": items})
        return items[index]

    def update_presence(
        self,
        member_id: str,
        status: str,
        room: str | None = None,
    ) -> dict[str, Any]:
        items = self.list()
        index = next((i for i, item in enumerate(items) if item["id"] == member_id), None)
        if index is None:
            raise KeyError(f"Member not found: {member_id}")

        now = utc_now()
        items[index]["presence"] = {
            "status": status,
            "room": room,
            "updated_at": now,
        }
        items[index]["updated_at"] = now
        self._write({"schema_version": 1, "members": items})
        return items[index]

    def delete(self, member_id: str) -> bool:
        items = self.list()
        remaining = [item for item in items if item["id"] != member_id]
        if len(remaining) == len(items):
            return False
        self._write({"schema_version": 1, "members": remaining})
        return True


family_profiles = FamilyProfileStore()
