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


class PrayerStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "prayer_intelligence.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

        if not self.path.exists():
            self.write({
                "settings": {
                    "latitude": 43.6532,
                    "longitude": -79.3832,
                    "timezone": "America/Toronto",
                    "fajr_angle": 18.0,
                    "isha_angle": 17.0,
                    "asr_factor": 1.0,
                    "adhan_enabled": True,
                    "pre_prayer_minutes": 10,
                    "iqamah_minutes": {
                        "fajr": 20,
                        "dhuhr": 15,
                        "asr": 15,
                        "maghrib": 10,
                        "isha": 15
                    },
                    "friday_mode": True,
                    "ramadan_mode": False
                },
                "events": [],
                "acknowledgements": []
            })

    def read(self) -> dict[str, Any]:
        with self.lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("settings", {})
        data.setdefault("events", [])
        data.setdefault("acknowledgements", [])
        return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            fd, tmp = tempfile.mkstemp(
                prefix="prayer-intelligence-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def update_settings(self, changes: dict[str, Any]) -> dict[str, Any]:
        data = self.read()
        data["settings"] = {
            **data["settings"],
            **changes,
        }
        self.write(data)
        return data["settings"]

    def add_event(self, item: dict[str, Any]) -> dict[str, Any]:
        data = self.read()
        event = {
            "created_at": utc_now(),
            **item,
        }
        data["events"].append(event)
        data["events"] = data["events"][-5000:]
        self.write(data)
        return event

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self.read()["events"]))[:limit]

    def acknowledge(self, prayer: str, prayer_date: str) -> dict[str, Any]:
        data = self.read()
        item = {
            "created_at": utc_now(),
            "prayer": prayer,
            "date": prayer_date,
        }
        data["acknowledgements"].append(item)
        data["acknowledgements"] = data["acknowledgements"][-2000:]
        self.write(data)
        return item


prayer_store = PrayerStore()
