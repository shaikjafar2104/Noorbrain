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


class ESP32Registry:
    def __init__(self, path: Path | None = None) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = path or project / "data" / "esp32_devices.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({"schema_version": 1, "devices": []})

    def _read(self) -> dict:
        with self._lock:
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Cannot read ESP32 registry: {exc}") from exc

    def _write(self, payload: dict) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="esp32-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def list(self) -> list[dict[str, Any]]:
        return list(self._read().get("devices", []))

    def get(self, device_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list() if item["id"] == device_id), None)

    def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        devices = self.list()

        device_id = str(
            payload.get("id")
            or payload.get("device_id")
            or uuid4().hex
        )

        now = utc_now()
        existing_index = next(
            (i for i, item in enumerate(devices) if item["id"] == device_id),
            None,
        )

        record = {
            "id": device_id,
            "name": str(payload.get("name") or device_id),
            "room": str(payload.get("room") or "Unassigned"),
            "ip_address": payload.get("ip_address"),
            "mac_address": payload.get("mac_address"),
            "firmware": payload.get("firmware"),
            "capabilities": list(payload.get("capabilities") or []),
            "online": True,
            "last_seen": now,
            "created_at": now,
            "updated_at": now,
            "metadata": dict(payload.get("metadata") or {}),
        }

        if existing_index is None:
            devices.append(record)
        else:
            original = devices[existing_index]
            record["created_at"] = original.get("created_at", now)
            devices[existing_index] = {**original, **record}

        self._write({
            "schema_version": 1,
            "updated_at": now,
            "devices": devices,
        })
        return record

    def heartbeat(self, device_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        devices = self.list()
        index = next(
            (i for i, item in enumerate(devices) if item["id"] == device_id),
            None,
        )
        if index is None:
            raise KeyError(f"ESP32 device not found: {device_id}")

        now = utc_now()
        patch = dict(payload or {})
        devices[index].update(patch)
        devices[index]["online"] = True
        devices[index]["last_seen"] = now
        devices[index]["updated_at"] = now

        self._write({
            "schema_version": 1,
            "updated_at": now,
            "devices": devices,
        })
        return devices[index]

    def mark_offline(self, device_id: str) -> dict[str, Any]:
        devices = self.list()
        index = next(
            (i for i, item in enumerate(devices) if item["id"] == device_id),
            None,
        )
        if index is None:
            raise KeyError(f"ESP32 device not found: {device_id}")

        devices[index]["online"] = False
        devices[index]["updated_at"] = utc_now()

        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "devices": devices,
        })
        return devices[index]


esp32_registry = ESP32Registry()
