from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from threading import RLock
from typing import Any

class FamilyStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "family_ai.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        if not self.path.exists():
            self.write({"profiles": [], "preferences": {}})

    def read(self) -> dict[str, Any]:
        with self.lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload.setdefault("profiles", [])
        payload.setdefault("preferences", {})
        return payload

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            fd, tmp = tempfile.mkstemp(prefix="family-ai-", suffix=".tmp", dir=str(self.path.parent))
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

family_store = FamilyStore()
