from __future__ import annotations

import math
from array import array
from typing import Optional


class NoiseFilter:
    """
    Python 3.13+ compatible PCM16 audio filter.

    Expected input:
        mono, signed 16-bit little-endian PCM bytes
    """

    def __init__(
        self,
        noise_threshold: int = 250,
        gain: float = 1.0,
    ) -> None:
        self.noise_threshold = max(0, int(noise_threshold))
        self.gain = max(0.0, float(gain))

    @staticmethod
    def _samples(audio_data: bytes) -> array:
        samples = array("h")
        samples.frombytes(audio_data)

        # Raspberry Pi/Ubuntu is normally little-endian.
        # This keeps the implementation explicit and portable.
        import sys

        if sys.byteorder != "little":
            samples.byteswap()

        return samples

    @staticmethod
    def _to_bytes(samples: array) -> bytes:
        import sys

        if sys.byteorder != "little":
            samples.byteswap()

        return samples.tobytes()

    def rms(self, audio_data: bytes) -> float:
        if not audio_data:
            return 0.0

        samples = self._samples(audio_data)
        if not samples:
            return 0.0

        square_sum = sum(sample * sample for sample in samples)
        return math.sqrt(square_sum / len(samples))

    def is_silence(
        self,
        audio_data: bytes,
        threshold: Optional[int] = None,
    ) -> bool:
        active_threshold = (
            self.noise_threshold
            if threshold is None
            else max(0, int(threshold))
        )

        return self.rms(audio_data) < active_threshold

    def suppress_noise(self, audio_data: bytes) -> bytes:
        if not audio_data:
            return b""

        samples = self._samples(audio_data)
        filtered = array("h")

        for sample in samples:
            if abs(sample) < self.noise_threshold:
                filtered.append(0)
                continue

            adjusted = int(sample * self.gain)
            adjusted = max(-32768, min(32767, adjusted))
            filtered.append(adjusted)

        return self._to_bytes(filtered)

    def normalize(
        self,
        audio_data: bytes,
        target_peak: int = 28000,
    ) -> bytes:
        if not audio_data:
            return b""

        samples = self._samples(audio_data)
        if not samples:
            return b""

        current_peak = max(abs(sample) for sample in samples)
        if current_peak == 0:
            return audio_data

        target_peak = max(1, min(32767, int(target_peak)))
        scale = target_peak / current_peak

        normalized = array(
            "h",
            (
                max(-32768, min(32767, int(sample * scale)))
                for sample in samples
            ),
        )

        return self._to_bytes(normalized)

    def process(self, audio_data: bytes) -> bytes:
        """
        Main pipeline-compatible method.
        """
        if not audio_data:
            return b""

        if self.is_silence(audio_data):
            return bytes(len(audio_data))

        return self.suppress_noise(audio_data)

    # Compatibility aliases for earlier pipeline implementations.
    filter = process
    apply = process
