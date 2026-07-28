from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from threading import RLock
from typing import Any

class SmartHomeStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "smart_home_runtime.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        if not self.path.exists():
            self.write({"rooms": [], "devices": [], "scenes": []})

    def read(self) -> dict[str, Any]:
        with self.lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload.setdefault("rooms", [])
        payload.setdefault("devices", [])
        payload.setdefault("scenes", [])
        return payload

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            fd, tmp = tempfile.mkstemp(prefix="smart-home-", suffix=".tmp", dir=str(self.path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as h:
                    json.dump(payload, h, indent=2, ensure_ascii=False)
                    h.write("\n")
                    h.flush()
                    os.fsync(h.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        return payload

    def summary(self) -> dict[str, Any]:
        data = self.read()
        online = sum(1 for d in data["devices"] if d.get("online"))
        return {
            "status": "ok",
            "room_count": len(data["rooms"]),
            "device_count": len(data["devices"]),
            "online_devices": online,
            "scene_count": len(data["scenes"]),
        }

smart_home_store = SmartHomeStore()
