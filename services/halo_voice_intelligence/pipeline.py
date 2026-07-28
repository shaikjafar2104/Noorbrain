from __future__ import annotations

from typing import Any

from .stt_service import stt_service
from .vad_service import vad_service
from .wakeword_service import wakeword_service


class VoiceIntelligencePipeline:
    def process_text(self, text: str) -> dict[str, Any]:
        wake = wakeword_service.detect(text)

        if wake["detected"]:
            command = text[len(wake["phrase"]):].strip(" ,:-")

            return {
                "status": "awake" if not command else "command",
                "wakeword": wake,
                "command": command,
            }

        return {
            "status": "ignored",
            "wakeword": wake,
            "command": "",
        }

    def process_audio(
        self,
        audio: bytes,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
        backend: str = "auto",
    ) -> dict[str, Any]:
        vad = vad_service.analyze_pcm16(audio)

        if not vad["speech_detected"]:
            return {
                "status": "silence",
                "vad": vad,
                "stt": None,
            }

        stt = stt_service.transcribe(
            audio,
            sample_rate=sample_rate,
            channels=channels,
            backend=backend,
        )

        return {
            "status": "ok" if stt.get("status") == "ok" else "degraded",
            "vad": vad,
            "stt": stt,
        }


voice_intelligence_pipeline = VoiceIntelligencePipeline()
