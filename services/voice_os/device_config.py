from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any


class VoiceDeviceConfig:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "voice_device_config.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self.write({
                "input_device": None,
                "output_device": None,
                "sample_rate": 16000,
                "channels": 1,
                "stt_backend": "auto",
                "tts_backend": "auto",
                "language": "en-US",
            })

    def read(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Voice device config is unreadable: {exc}") from exc

            if not isinstance(payload, dict):
                raise RuntimeError("Voice device config must be a JSON object.")

            return payload

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        clean = {
            "input_device": payload.get("input_device"),
            "output_device": payload.get("output_device"),
            "sample_rate": int(payload.get("sample_rate", 16000)),
            "channels": int(payload.get("channels", 1)),
            "stt_backend": str(payload.get("stt_backend", "auto")),
            "tts_backend": str(payload.get("tts_backend", "auto")),
            "language": str(payload.get("language", "en-US")),
        }

        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="voice-device-config-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(clean, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

        return clean

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.read()
        current.update(patch)
        return self.write(current)


voice_device_config = VoiceDeviceConfig()
