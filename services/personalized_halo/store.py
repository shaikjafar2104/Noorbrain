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


class PersonalizedHALOStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "personalized_halo.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

        if not self.path.exists():
            self.write({
                "settings": {
                    "enabled": True,
                    "cooldown_seconds": 900,
                    "morning_start": 4,
                    "afternoon_start": 12,
                    "evening_start": 17,
                    "night_start": 21,
                },
                "events": [],
                "last_greetings": {},
            })

    def read(self) -> dict[str, Any]:
        with self.lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("settings", {})
        data.setdefault("events", [])
        data.setdefault("last_greetings", {})
        return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            fd, tmp = tempfile.mkstemp(
                prefix="personalized-halo-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(
                        data,
                        handle,
                        indent=2,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def update_settings(
        self,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        data = self.read()
        data["settings"] = {
            **data["settings"],
            **changes,
        }
        self.write(data)
        return data["settings"]

    def record_greeting(
        self,
        *,
        profile_id: str,
        greeting: dict[str, Any],
    ) -> dict[str, Any]:
        data = self.read()
        event = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            **greeting,
        }
        data["events"].append(event)
        data["events"] = data["events"][-5000:]
        data["last_greetings"][profile_id] = event["created_at"]
        self.write(data)
        return event

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self.read()["events"]))[:limit]


personalized_halo_store = PersonalizedHALOStore()
