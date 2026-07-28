from __future__ import annotations

from typing import Any

from .tts_service import streaming_tts_service


def voice_stack_status() -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "healthy",
        "components": {},
    }

    probes = {
        "runtime": (
            "services.halo_runtime.runtime",
            "halo_runtime_manager",
            "status",
        ),
        "audio": (
            "services.halo_audio.service",
            "halo_audio_service",
            "status",
        ),
        "wakeword": (
            "services.halo_voice_intelligence.wakeword_service",
            "wakeword_service",
            "status",
        ),
        "vad": (
            "services.halo_voice_intelligence.vad_service",
            "vad_service",
            "status",
        ),
        "stt": (
            "services.halo_voice_intelligence.stt_service",
            "stt_service",
            "health",
        ),
    }

    for name, (module_name, object_name, method_name) in probes.items():
        try:
            module = __import__(module_name, fromlist=[object_name])
            instance = getattr(module, object_name)
            method = getattr(instance, method_name)
            value = method()
        except Exception as exc:
            value = {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }
            result["status"] = "degraded"

        result["components"][name] = value

    result["components"]["tts"] = streaming_tts_service.status()
    return result
