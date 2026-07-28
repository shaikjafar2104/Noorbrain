from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from .models import AudioConfig


class AudioConfigStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "halo_audio_config.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self.write(AudioConfig())

    def read(self) -> AudioConfig:
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        return AudioConfig.model_validate(payload)

    def write(self, config: AudioConfig | dict[str, Any]) -> AudioConfig:
        item = config if isinstance(config, AudioConfig) else AudioConfig.model_validate(config)

        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="halo-audio-config-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(item.model_dump(mode="json"), handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

        return item

    def update(self, patch: dict[str, Any]) -> AudioConfig:
        payload = self.read().model_dump()
        payload.update(patch)
        return self.write(payload)


audio_config_store = AudioConfigStore()
