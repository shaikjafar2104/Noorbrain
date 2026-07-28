from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from threading import RLock
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class IslamicReminderStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "islamic_reminders.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

        if not self.path.exists():
            self.write({
                "mappings": self._defaults(),
                "events": [],
                "preferences": {},
            })

    @staticmethod
    def _defaults() -> list[dict[str, Any]]:
        return [
            {
                "id": "kitchen-enter",
                "name": "Kitchen Bismillah",
                "enabled": True,
                "trigger": {"event_type": "person_entered", "zone": "Kitchen"},
                "message": "Say Bismillah before eating.",
                "category": "meal",
                "cooldown_seconds": 300,
                "priority": 5,
            },
            {
                "id": "home-exit",
                "name": "Leaving Home Dua",
                "enabled": True,
                "trigger": {"event_type": "person_exited", "zone": "Entrance"},
                "message": "Recite the leaving home dua and Ayatul Kursi.",
                "category": "protection",
                "cooldown_seconds": 600,
                "priority": 5,
            },
            {
                "id": "bedroom-night",
                "name": "Bedtime Dua",
                "enabled": True,
                "trigger": {"event_type": "person_entered", "zone": "Bedroom", "time_window": "night"},
                "message": "Remember the bedtime dua and recite Ayatul Kursi.",
                "category": "bedtime",
                "cooldown_seconds": 1800,
                "priority": 4,
            },
            {
                "id": "prayer-space",
                "name": "Prayer Preparation",
                "enabled": True,
                "trigger": {"event_type": "person_entered", "zone": "Prayer"},
                "message": "Prepare for Salah and renew your intention.",
                "category": "salah",
                "cooldown_seconds": 900,
                "priority": 5,
            },
            {
                "id": "morning-azkar",
                "name": "Morning Azkar",
                "enabled": True,
                "trigger": {"event_type": "time", "time_window": "morning"},
                "message": "It is time for morning Azkar.",
                "category": "azkar",
                "cooldown_seconds": 21600,
                "priority": 4,
            },
            {
                "id": "evening-azkar",
                "name": "Evening Azkar",
                "enabled": True,
                "trigger": {"event_type": "time", "time_window": "evening"},
                "message": "It is time for evening Azkar.",
                "category": "azkar",
                "cooldown_seconds": 21600,
                "priority": 4,
            },
        ]

    def read(self) -> dict[str, Any]:
        with self.lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("mappings", [])
        data.setdefault("events", [])
        data.setdefault("preferences", {})
        return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            fd, tmp = tempfile.mkstemp(prefix="islamic-reminders-", suffix=".tmp", dir=str(self.path.parent))
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

    def list_mappings(self) -> list[dict[str, Any]]:
        return list(self.read()["mappings"])

    def save_mapping(self, item: dict[str, Any]) -> dict[str, Any]:
        data = self.read()
        mapping = {
            "id": item.get("id") or uuid4().hex,
            "created_at": item.get("created_at") or utc_now(),
            "enabled": True,
            "cooldown_seconds": 300,
            "priority": 5,
            **item,
            "updated_at": utc_now(),
        }
        data["mappings"] = [x for x in data["mappings"] if x.get("id") != mapping["id"]]
        data["mappings"].append(mapping)
        self.write(data)
        return mapping

    def delete_mapping(self, mapping_id: str) -> int:
        data = self.read()
        before = len(data["mappings"])
        data["mappings"] = [x for x in data["mappings"] if x.get("id") != mapping_id]
        removed = before - len(data["mappings"])
        self.write(data)
        return removed

    def add_event(self, item: dict[str, Any]) -> dict[str, Any]:
        data = self.read()
        event = {"id": uuid4().hex, "created_at": utc_now(), **item}
        data["events"].append(event)
        data["events"] = data["events"][-5000:]
        self.write(data)
        return event

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self.read()["events"]))[:limit]

islamic_reminder_store = IslamicReminderStore()
