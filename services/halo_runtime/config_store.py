from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from .models import RuntimeConfig


class RuntimeConfigStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "halo_runtime_config.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self.write(RuntimeConfig())

    def read(self) -> RuntimeConfig:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Runtime config is unreadable: {exc}") from exc

        return RuntimeConfig.model_validate(payload)

    def write(self, config: RuntimeConfig | dict[str, Any]) -> RuntimeConfig:
        item = (
            config
            if isinstance(config, RuntimeConfig)
            else RuntimeConfig.model_validate(config)
        )

        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="halo-runtime-config-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(
                        item.model_dump(mode="json"),
                        handle,
                        indent=2,
                        sort_keys=True,
                    )
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

        return item

    def update(self, patch: dict[str, Any]) -> RuntimeConfig:
        payload = self.read().model_dump()
        payload.update(patch)
        return self.write(payload)


runtime_config_store = RuntimeConfigStore()
