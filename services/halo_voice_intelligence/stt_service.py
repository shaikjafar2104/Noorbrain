from __future__ import annotations

from typing import Any


class HALOSTTService:
    def health(self) -> dict[str, Any]:
        try:
            from services.voice_os.offline_stt import offline_stt
            return offline_stt.health()
        except Exception as exc:
            return {
                "status": "unavailable",
                "reason": f"{type(exc).__name__}: {exc}",
            }

    def transcribe(
        self,
        audio: bytes,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
        backend: str = "auto",
    ) -> dict[str, Any]:
        from services.voice_os.offline_stt import offline_stt

        return offline_stt.transcribe_pcm16(
            audio,
            sample_rate=sample_rate,
            channels=channels,
            backend=backend,
        )


stt_service = HALOSTTService()
