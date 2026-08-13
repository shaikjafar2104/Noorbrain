from __future__ import annotations

import re
import time
from threading import RLock
from typing import Any


class WakeWordService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._wake_words = {"halo", "hey halo", "hello halo"}
        self._armed_until = 0.0
        self._last_detection: dict[str, Any] | None = None

    def configure(self, wake_words: list[str]) -> dict[str, Any]:
        cleaned = {
            re.sub(r"\s+", " ", item.strip().casefold())
            for item in wake_words
            if item and item.strip()
        }

        if not cleaned:
            raise ValueError("At least one wake word is required.")

        with self._lock:
            self._wake_words = cleaned

        return self.status()

    def detect(self, text: str) -> dict[str, Any]:
        normalized = re.sub(r"\s+", " ", text.strip().casefold())

        with self._lock:
            match = next(
                (
                    item
                    for item in sorted(self._wake_words, key=len, reverse=True)
                    if normalized == item or normalized.startswith(item + " ")
                ),
                None,
            )

            detected = match is not None
            if detected:
                self._armed_until = time.monotonic() + 10.0

            self._last_detection = {
                "detected": detected,
                "phrase": match or "",
                "confidence": 1.0 if detected else 0.0,
                "timestamp": time.time(),
            }

            return {
                **self._last_detection,
                "armed": self.is_armed(),
            }

    def is_armed(self) -> bool:
        with self._lock:
            return time.monotonic() < self._armed_until

    def disarm(self) -> None:
        with self._lock:
            self._armed_until = 0.0

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": "ready",
                "wake_words": sorted(self._wake_words),
                "armed": time.monotonic() < self._armed_until,
                "last_detection": self._last_detection,
            }


wakeword_service = WakeWordService()
