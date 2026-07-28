from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from .manager import device_manager


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeviceGroupManager:
    def __init__(self, path: Path | None = None) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = path or project / "data" / "device_groups.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({"schema_version": 1, "groups": []})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="groups-",
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
        return list(self._read().get("groups", []))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        device_ids = list(payload.get("device_ids") or [])

        if not name:
            raise ValueError("Group name is required.")

        now = utc_now()
        group = {
            "id": uuid4().hex,
            "name": name,
            "room": str(payload.get("room") or "Unassigned"),
            "device_ids": device_ids,
            "created_at": now,
            "updated_at": now,
        }

        groups = self.list()
        groups.append(group)
        self._write({"schema_version": 1, "updated_at": now, "groups": groups})
        return group

    def update(self, group_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        groups = self.list()
        index = next((i for i, item in enumerate(groups) if item["id"] == group_id), None)
        if index is None:
            raise KeyError(f"Group not found: {group_id}")

        protected = {"id", "created_at"}
        for key, value in patch.items():
            if key not in protected:
                groups[index][key] = value

        groups[index]["updated_at"] = utc_now()
        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "groups": groups,
        })
        return groups[index]

    def delete(self, group_id: str) -> bool:
        groups = self.list()
        remaining = [item for item in groups if item["id"] != group_id]
        if len(remaining) == len(groups):
            return False

        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "groups": remaining,
        })
        return True

    def control(self, group_id: str, action: str) -> dict[str, Any]:
        group = next((item for item in self.list() if item["id"] == group_id), None)
        if group is None:
            raise KeyError(f"Group not found: {group_id}")

        results = []

        for device_id in group.get("device_ids", []):
            try:
                if action == "on":
                    device = device_manager.set_state(device_id, "on")
                elif action == "off":
                    device = device_manager.set_state(device_id, "off")
                elif action == "toggle":
                    device = device_manager.toggle(device_id)
                else:
                    raise ValueError(f"Unsupported group action: {action}")

                results.append({
                    "status": "ok",
                    "device": device.model_dump(mode="json"),
                })
            except Exception as exc:
                results.append({
                    "status": "error",
                    "device_id": device_id,
                    "reason": str(exc),
                })

        return {
            "status": "ok",
            "group": group,
            "action": action,
            "results": results,
        }


group_manager = DeviceGroupManager()
