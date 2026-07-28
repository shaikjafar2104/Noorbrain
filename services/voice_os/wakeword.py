from __future__ import annotations

import re
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass
class WakeWordEvent:
    detected: bool
    phrase: str
    confidence: float
    timestamp: float


class WakeWordEngine:
    def __init__(self) -> None:
        self._lock = RLock()
        self._wake_words = {"halo", "hey halo", "hello halo"}
        self._armed_until = 0.0
        self._last_event: dict[str, Any] | None = None

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

    def detect_text(self, text: str) -> WakeWordEvent:
        normalized = re.sub(r"\s+", " ", text.strip().casefold())

        with self._lock:
            matched = next(
                (
                    wake_word
                    for wake_word in sorted(
                        self._wake_words,
                        key=len,
                        reverse=True,
                    )
                    if normalized == wake_word
                    or normalized.startswith(wake_word + " ")
                ),
                None,
            )

            event = WakeWordEvent(
                detected=matched is not None,
                phrase=matched or "",
                confidence=1.0 if matched else 0.0,
                timestamp=time.time(),
            )

            if matched:
                self._armed_until = time.monotonic() + 12.0

            self._last_event = {
                "detected": event.detected,
                "phrase": event.phrase,
                "confidence": event.confidence,
                "timestamp": event.timestamp,
            }

            return event

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
                "last_event": self._last_event,
            }


wakeword_engine = WakeWordEngine()
