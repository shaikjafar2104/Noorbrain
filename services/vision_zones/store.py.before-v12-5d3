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


class ZoneStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "vision_zones.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({
                "schema_version": 1,
                "zones": [],
                "motion_events": [],
            })

    def _read(self) -> dict[str, Any]:
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))

        if not isinstance(payload, dict):
            raise RuntimeError("Vision zone store must be a JSON object.")

        payload.setdefault("schema_version", 1)
        payload.setdefault("zones", [])
        payload.setdefault("motion_events", [])
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="vision-zones-",
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

    def list_zones(self) -> list[dict[str, Any]]:
        return list(self._read()["zones"])

    def save_zone(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()

        zone = {
            "id": item.get("id") or uuid4().hex,
            "created_at": item.get("created_at") or utc_now(),
            "updated_at": utc_now(),
            **item,
        }

        payload["zones"] = [
            current
            for current in payload["zones"]
            if current.get("id") != zone["id"]
        ]
        payload["zones"].append(zone)
        self._write(payload)
        return zone

    def delete_zone(self, zone_id: str) -> int:
        payload = self._read()
        before = len(payload["zones"])
        payload["zones"] = [
            zone
            for zone in payload["zones"]
            if zone.get("id") != zone_id
        ]
        removed = before - len(payload["zones"])
        self._write(payload)
        return removed

    def add_motion_event(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()
        event = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            **item,
        }
        payload["motion_events"].append(event)
        payload["motion_events"] = payload["motion_events"][-5000:]
        self._write(payload)
        return event

    def list_motion_events(
        self,
        *,
        limit: int = 100,
        zone_id: str | None = None,
    ) -> list[dict[str, Any]]:
        events = list(reversed(self._read()["motion_events"]))

        if zone_id:
            events = [
                event
                for event in events
                if event.get("zone_id") == zone_id
            ]

        return events[:limit]

    def clear_motion_events(self) -> int:
        payload = self._read()
        removed = len(payload["motion_events"])
        payload["motion_events"] = []
        self._write(payload)
        return removed


zone_store = ZoneStore()
