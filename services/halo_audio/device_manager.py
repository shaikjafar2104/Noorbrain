from __future__ import annotations

import time
from typing import Any

from .config_store import audio_config_store


class AudioDeviceManager:
    def list_devices(self) -> dict[str, Any]:
        try:
            import sounddevice as sd  # type: ignore
        except Exception as exc:
            return {
                "status": "unavailable",
                "devices": [],
                "reason": f"{type(exc).__name__}: {exc}",
            }

        devices = []
        for index, item in enumerate(sd.query_devices()):
            devices.append({
                "index": index,
                "name": str(item.get("name", "")),
                "max_input_channels": int(item.get("max_input_channels", 0)),
                "max_output_channels": int(item.get("max_output_channels", 0)),
                "default_samplerate": float(item.get("default_samplerate", 0.0)),
            })

        return {
            "status": "ok",
            "devices": devices,
            "default_input": sd.default.device[0],
            "default_output": sd.default.device[1],
        }

    def health(self) -> dict[str, Any]:
        started = time.perf_counter()
        result = self.list_devices()
        devices = result.get("devices", [])

        input_count = sum(
            1 for item in devices
            if item.get("max_input_channels", 0) > 0
        )
        output_count = sum(
            1 for item in devices
            if item.get("max_output_channels", 0) > 0
        )

        return {
            "status": (
                "healthy"
                if result.get("status") == "ok" and input_count and output_count
                else "degraded"
            ),
            "input_count": input_count,
            "output_count": output_count,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "config": audio_config_store.read().model_dump(mode="json"),
            "backend": result,
        }


audio_device_manager = AudioDeviceManager()
