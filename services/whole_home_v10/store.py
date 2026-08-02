from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class WholeHomeStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "data" / "whole_home_v10.json"
        self.lock = threading.RLock()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "10.0.0",
            "rooms": [
                {"id": "hall", "name": "Hall", "icon": "🛋️"},
                {"id": "bedroom", "name": "Bedroom", "icon": "🛏️"},
                {"id": "kitchen", "name": "Kitchen", "icon": "🍳"},
            ],
            "devices": [],
            "scenes": [],
            "automations": [],
            "runs": [],
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
            for key in ("rooms", "devices", "scenes", "automations", "runs"):
                if isinstance(data.get(key), list):
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
        return {
            "rooms": data["rooms"],
            "devices": data["devices"],
            "scenes": data["scenes"],
            "automations": data["automations"],
            "runs": data["runs"][-25:],
            "summary": {
                "rooms": len(data["rooms"]),
                "devices": len(data["devices"]),
                "online": sum(1 for item in data["devices"] if item.get("online", True)),
                "powered_on": sum(1 for item in data["devices"] if item.get("state", {}).get("power")),
                "scenes": len(data["scenes"]),
                "automations": len(data["automations"]),
            },
        }

    def add_room(self, name: str, icon: str) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            room = {"id": uuid4().hex, "name": name, "icon": icon or "🏠"}
            data["rooms"].append(room)
            self.write(data)
            return room

    def add_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            device = {
                "id": uuid4().hex,
                "name": payload["name"],
                "type": payload.get("type", "switch"),
                "room_id": payload.get("room_id", "hall"),
                "online": True,
                "state": {"power": bool(payload.get("power", False))},
                "created_at": self.now(),
            }
            data["devices"].append(device)
            self.write(data)
            return device

    def set_device(self, device_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            device = next((item for item in data["devices"] if item["id"] == device_id), None)
            if device is None:
                return None
            if "power" in patch:
                device.setdefault("state", {})["power"] = bool(patch["power"])
            if "online" in patch:
                device["online"] = bool(patch["online"])
            if str(patch.get("name") or "").strip():
                device["name"] = str(patch["name"]).strip()
            device["updated_at"] = self.now()
            self.write(data)
            return device

    def delete_device(self, device_id: str) -> bool:
        with self.lock:
            data = self.read()
            before = len(data["devices"])
            data["devices"] = [item for item in data["devices"] if item["id"] != device_id]
            removed = len(data["devices"]) != before
            if removed:
                self.write(data)
            return removed

    def add_scene(self, name: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            scene = {"id": uuid4().hex, "name": name, "actions": actions, "created_at": self.now()}
            data["scenes"].append(scene)
            self.write(data)
            return scene

    def run_actions(self, data: dict[str, Any], actions: list[dict[str, Any]]) -> int:
        changed = 0
        for action in actions:
            device = next((item for item in data["devices"] if item["id"] == action.get("device_id")), None)
            if device is not None and "power" in action:
                device.setdefault("state", {})["power"] = bool(action["power"])
                changed += 1
        return changed

    def run_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            scene = next((item for item in data["scenes"] if item["id"] == scene_id), None)
            if scene is None:
                return None
            changed = self.run_actions(data, scene.get("actions", []))
            run = {"id": uuid4().hex, "kind": "scene", "source_id": scene_id, "changed": changed, "at": self.now()}
            data["runs"].append(run); data["runs"] = data["runs"][-200:]
            self.write(data)
            return run

    def delete_scene(self, scene_id: str) -> bool:
        with self.lock:
            data = self.read(); before = len(data["scenes"])
            data["scenes"] = [item for item in data["scenes"] if item["id"] != scene_id]
            removed = len(data["scenes"]) != before
            if removed: self.write(data)
            return removed

    def add_automation(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            automation = {
                "id": uuid4().hex, "name": payload["name"],
                "trigger": payload.get("trigger", {"kind": "manual"}),
                "actions": payload.get("actions", []), "enabled": True,
                "created_at": self.now(),
            }
            data["automations"].append(automation); self.write(data); return automation

    def run_automation(self, automation_id: str) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            automation = next((item for item in data["automations"] if item["id"] == automation_id), None)
            if automation is None or not automation.get("enabled", True): return None
            changed = self.run_actions(data, automation.get("actions", []))
            run = {"id": uuid4().hex, "kind": "automation", "source_id": automation_id, "changed": changed, "at": self.now()}
            data["runs"].append(run); data["runs"] = data["runs"][-200:]; self.write(data); return run

    def delete_automation(self, automation_id: str) -> bool:
        with self.lock:
            data = self.read(); before = len(data["automations"])
            data["automations"] = [item for item in data["automations"] if item["id"] != automation_id]
            removed = len(data["automations"]) != before
            if removed: self.write(data)
            return removed


whole_home_store = WholeHomeStore()
