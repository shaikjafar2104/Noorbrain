from __future__ import annotations

import importlib.util
from typing import Any, Dict


class SpeakerManager:
    def status(self) -> Dict[str, Any]:
        """
        Lightweight non-blocking status.

        Device enumeration is intentionally deferred because PortAudio/ALSA
        probing may block the API request.
        """
        installed = importlib.util.find_spec("sounddevice") is not None

        return {
            "available": installed,
            "backend": "sounddevice" if installed else None,
            "package_installed": installed,
            "device_probe": "deferred",
            "output_devices": [],
        }

    def list_output_devices(self) -> Dict[str, Any]:
        try:
            import sounddevice as sd  # type: ignore

            devices = sd.query_devices()
            outputs = []

            for index, device in enumerate(devices):
                if int(device.get("max_output_channels", 0)) > 0:
                    outputs.append(
                        {
                            "index": index,
                            "name": str(device.get("name", "unknown")),
                            "channels": int(
                                device.get("max_output_channels", 0)
                            ),
                            "sample_rate": float(
                                device.get("default_samplerate", 0)
                            ),
                        }
                    )

            return {
                "status": "ok",
                "available": bool(outputs),
                "output_devices": outputs,
            }

        except Exception as exc:
            return {
                "status": "unavailable",
                "available": False,
                "output_devices": [],
                "reason": str(exc),
            }
