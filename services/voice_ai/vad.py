from __future__ import annotations

import math
from array import array
from dataclasses import dataclass
from typing import Optional


@dataclass
class VADResult:
    is_speech: bool
    rms: float
    peak: int
    threshold: int
    speech_ratio: float

    def to_dict(self) -> dict:
        return {
            "is_speech": self.is_speech,
            "rms": round(self.rms, 2),
            "peak": self.peak,
            "threshold": self.threshold,
            "speech_ratio": round(self.speech_ratio, 4),
        }


class VoiceActivityDetector:
    """
    Python 3.13+ compatible PCM16 Voice Activity Detector.

    Expected input:
        mono, signed 16-bit little-endian PCM bytes
    """

    def __init__(
        self,
        threshold: int = 350,
        min_speech_ratio: float = 0.02,
        frame_ms: int = 30,
        sample_rate: int = 16000,
    ) -> None:
        self.threshold = max(1, int(threshold))
        self.min_speech_ratio = max(
            0.0,
            min(1.0, float(min_speech_ratio)),
        )
        self.frame_ms = max(10, int(frame_ms))
        self.sample_rate = max(8000, int(sample_rate))

    @staticmethod
    def _samples(audio_data: bytes) -> array:
        samples = array("h")
        samples.frombytes(audio_data)

        import sys

        if sys.byteorder != "little":
            samples.byteswap()

        return samples

    @staticmethod
    def _rms(samples: array) -> float:
        if not samples:
            return 0.0

        square_sum = sum(sample * sample for sample in samples)
        return math.sqrt(square_sum / len(samples))

    def analyze(
        self,
        audio_data: bytes,
        threshold: Optional[int] = None,
    ) -> VADResult:
        active_threshold = (
            self.threshold
            if threshold is None
            else max(1, int(threshold))
        )

        if not audio_data:
            return VADResult(
                is_speech=False,
                rms=0.0,
                peak=0,
                threshold=active_threshold,
                speech_ratio=0.0,
            )

        samples = self._samples(audio_data)

        if not samples:
            return VADResult(
                is_speech=False,
                rms=0.0,
                peak=0,
                threshold=active_threshold,
                speech_ratio=0.0,
            )

        rms_value = self._rms(samples)
        peak = max(abs(sample) for sample in samples)

        active_samples = sum(
            1 for sample in samples
            if abs(sample) >= active_threshold
        )

        speech_ratio = active_samples / len(samples)

        is_speech = (
            rms_value >= active_threshold
            and speech_ratio >= self.min_speech_ratio
        )

        return VADResult(
            is_speech=is_speech,
            rms=rms_value,
            peak=peak,
            threshold=active_threshold,
            speech_ratio=speech_ratio,
        )

    def is_speech(
        self,
        audio_data: bytes,
        threshold: Optional[int] = None,
    ) -> bool:
        return self.analyze(
            audio_data,
            threshold=threshold,
        ).is_speech

    def detect(
        self,
        audio_data: bytes,
        threshold: Optional[int] = None,
    ) -> bool:
        return self.is_speech(
            audio_data,
            threshold=threshold,
        )

    def process(
        self,
        audio_data: bytes,
    ) -> dict:
        return self.analyze(audio_data).to_dict()
