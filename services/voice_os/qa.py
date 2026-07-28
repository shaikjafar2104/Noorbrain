from __future__ import annotations

import time
from typing import Any

from .audio_devices import list_audio_devices
from .device_config import voice_device_config
from .offline_stt import offline_stt
from .offline_tts import offline_tts
from .wakeword import wakeword_engine


class VoiceQA:
    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        checks: list[dict[str, Any]] = []

        def check(name: str, fn) -> None:
            try:
                result = fn()
                passed = bool(result)
                checks.append({
                    "name": name,
                    "status": "PASS" if passed else "FAIL",
                    "detail": result,
                })
            except Exception as exc:
                checks.append({
                    "name": name,
                    "status": "FAIL",
                    "detail": f"{type(exc).__name__}: {exc}",
                })

        check("device_config", lambda: isinstance(voice_device_config.read(), dict))
        check("audio_discovery", lambda: "status" in list_audio_devices())
        check("wakeword", lambda: wakeword_engine.detect_text("HALO").detected)
        check("stt_health", lambda: "status" in offline_stt.health())
        check("tts_health", lambda: "status" in offline_tts.health())

        passed = sum(1 for item in checks if item["status"] == "PASS")
        failed = len(checks) - passed

        return {
            "status": "PASS" if failed == 0 else "FAIL",
            "passed": passed,
            "failed": failed,
            "checks": checks,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }


voice_qa = VoiceQA()
