from __future__ import annotations

import array
import math
from typing import Any


class VoiceActivityDetector:
    def __init__(self, threshold: float = 450.0) -> None:
        self.threshold = float(threshold)

    def configure(self, threshold: float) -> dict[str, Any]:
        if threshold <= 0:
            raise ValueError("VAD threshold must be greater than zero.")
        self.threshold = float(threshold)
        return self.status()

    def analyze_pcm16(self, audio: bytes) -> dict[str, Any]:
        if not audio:
            raise ValueError("No PCM audio received.")

        samples = array.array("h")
        samples.frombytes(audio)

        if not samples:
            raise ValueError("PCM audio contains no samples.")

        square_sum = sum(float(sample) ** 2 for sample in samples)
        rms = math.sqrt(square_sum / len(samples))
        peak = max(abs(sample) for sample in samples)
        speech = rms >= self.threshold

        return {
            "status": "ok",
            "speech_detected": speech,
            "rms": round(rms, 2),
            "peak": int(peak),
            "threshold": self.threshold,
            "sample_count": len(samples),
        }

    def status(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "backend": "pcm16-rms",
            "threshold": self.threshold,
        }


vad_service = VoiceActivityDetector()
