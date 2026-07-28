from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict

from .analytics import voice_analytics
from .diagnostics import voice_diagnostics


class VoiceDashboard:
    @staticmethod
    def _safe(call: Callable[[], Any], fallback: Any) -> Any:
        try:
            return call()
        except Exception as exc:
            if isinstance(fallback, dict):
                return {**fallback, "reason": str(exc)}
            return fallback

    def snapshot(self, orchestrator: Any, days: int = 30, recent_limit: int = 10) -> Dict[str, Any]:
        settings = self._safe(
            lambda: orchestrator.settings_store.load().model_dump(),
            {},
        )
        health = self._safe(
            orchestrator.health,
            {"status": "degraded", "service": "voice_ai"},
        )
        analytics = self._safe(
            lambda: voice_analytics.summary(days),
            {"status": "unavailable", "conversation_count": 0},
        )
        recent = self._safe(
            lambda: voice_analytics.recent(recent_limit),
            {"status": "unavailable", "count": 0, "turns": []},
        )
        diagnostics = self._safe(
            lambda: voice_diagnostics.snapshot(probe_hardware=False),
            {"status": "unavailable"},
        )
        components = {
            "audio": health.get("audio", {}),
            "stt": health.get("stt", {}),
            "tts": health.get("tts", {}),
            "speaker": health.get("speaker", {}),
            "memory": health.get("memory", {}),
        }
        available_count = sum(
            1 for component in components.values()
            if component.get("available") is True
        )
        return {
            "status": "ok",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "service_status": health.get("status", "unknown"),
            "version": health.get("version"),
            "wake_word": settings.get("wake_word", health.get("wake_word")),
            "enabled": settings.get("enabled", health.get("enabled")),
            "components": components,
            "available_component_count": available_count,
            "analytics": analytics,
            "recent_conversations": recent,
            "diagnostics_summary": {
                "python": diagnostics.get("python", {}),
                "database": diagnostics.get("database", {}),
                "vosk_model": diagnostics.get("vosk_model", {}),
                "hardware_probe": diagnostics.get("hardware_probe", {}),
            },
            "last_result": health.get("last_result"),
        }


voice_dashboard = VoiceDashboard()
