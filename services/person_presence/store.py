from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class PresenceStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "person_presence.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        if not self.path.exists():
            self.write({"active_tracks": {}, "events": []})

    def read(self) -> dict[str, Any]:
        with self.lock:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("active_tracks", {})
        data.setdefault("events", [])
        return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            fd, tmp = tempfile.mkstemp(prefix="presence-", suffix=".tmp", dir=str(self.path.parent))
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

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        data = self.read()
        item = {"created_at": utc_now(), **event}
        data["events"].append(item)
        data["events"] = data["events"][-5000:]
        self.write(data)
        return item

presence_store = PresenceStore()
