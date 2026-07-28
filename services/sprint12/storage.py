from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any


class JsonStore:
    def __init__(self, path: Path, root_key: str) -> None:
        self.path = path
        self.root_key = root_key
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self.write([])

    def read(self) -> list[dict[str, Any]]:
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            items = payload.get(self.root_key, [])
            if not isinstance(items, list):
                raise RuntimeError(f"{self.root_key} must be a list")
            return items

    def write(self, items: list[dict[str, Any]]) -> None:
        payload = {"schema_version": 1, self.root_key: items}
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix=f"{self.root_key}-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
