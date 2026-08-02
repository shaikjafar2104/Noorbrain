from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class FamilyIntelligenceStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "data" / "family_intelligence_v11.json"
        self.lock = threading.RLock()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "11.0.0",
            "members": [],
            "presence": {},
            "events": [],
            "privacy": {
                "recognition_enabled": True,
                "store_snapshots": False,
                "presence_history_enabled": True,
                "unknown_person_alerts": True,
            },
            "updated_at": self.now(),
        }

    def read(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.is_file():
                return self.default()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return self.default()
            base = self.default()
            for key in ("members", "presence", "events", "privacy"):
                if key in data and isinstance(data[key], type(base[key])):
                    if key == "privacy":
                        base[key].update(data[key])
                    else:
                        base[key] = data[key]
            return base

    def write(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = self.now()
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)
            return data

    def overview(self) -> dict[str, Any]:
        data = self.read()
        active = [item for item in data["presence"].values() if item.get("present")]
        return {
            "members": data["members"],
            "presence": data["presence"],
            "events": data["events"][-50:],
            "privacy": data["privacy"],
            "summary": {
                "members": len(data["members"]),
                "present": len(active),
                "rooms_active": len({item.get("room") for item in active if item.get("room")}),
                "events": len(data["events"]),
                "unknown_present": sum(
                    1 for item in active if item.get("identity") == "unknown"
                ),
            },
        }

    def add_member(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            member = {
                "id": uuid4().hex,
                "name": payload["name"],
                "role": payload.get("role", "family"),
                "preferred_language": payload.get("preferred_language", "en"),
                "reminders_enabled": bool(payload.get("reminders_enabled", True)),
                "created_at": self.now(),
            }
            data["members"].append(member)
            self.write(data)
            return member

    def update_member(self, member_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            member = next((item for item in data["members"] if item["id"] == member_id), None)
            if member is None:
                return None
            for key in ("name", "role", "preferred_language", "reminders_enabled"):
                if key in patch:
                    member[key] = patch[key]
            member["updated_at"] = self.now()
            self.write(data)
            return member

    def delete_member(self, member_id: str) -> bool:
        with self.lock:
            data = self.read()
            before = len(data["members"])
            data["members"] = [item for item in data["members"] if item["id"] != member_id]
            data["presence"].pop(member_id, None)
            removed = len(data["members"]) != before
            if removed:
                self.write(data)
            return removed

    def record_presence(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            identity = str(payload.get("member_id") or payload.get("identity") or "unknown")
            event = {
                "id": uuid4().hex,
                "identity": identity,
                "member_id": payload.get("member_id"),
                "room": str(payload.get("room") or "Unknown"),
                "present": bool(payload.get("present", True)),
                "confidence": max(0.0, min(float(payload.get("confidence", 0.0)), 1.0)),
                "source": str(payload.get("source") or "vision"),
                "at": self.now(),
            }
            data["presence"][identity] = event
            if data["privacy"].get("presence_history_enabled", True):
                data["events"].append(event)
                data["events"] = data["events"][-1000:]
            self.write(data)
            return event

    def update_privacy(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            for key in data["privacy"]:
                if key in patch:
                    data["privacy"][key] = bool(patch[key])
            self.write(data)
            return data["privacy"]


family_intelligence_store = FamilyIntelligenceStore()
