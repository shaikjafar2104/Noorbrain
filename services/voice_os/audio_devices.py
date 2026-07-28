from __future__ import annotations
from typing import Any

def list_audio_devices() -> dict[str, Any]:
    try:
        import sounddevice as sd
    except Exception as exc:
        return {"status": "unavailable", "devices": [], "reason": str(exc)}

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
