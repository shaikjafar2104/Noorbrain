from __future__ import annotations

import re
import threading
import time
from typing import Any
from uuid import uuid4

from services.halo_voice_context_v8.engine import voice_context_engine


class UniversalVoiceGateway:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.recent: dict[str, tuple[str, float]] = {}
        self.accepted = 0
        self.duplicates = 0
        self.errors = 0

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def prepare(
        self,
        session_id: str,
        transcript: str,
        source: str,
    ) -> dict[str, Any]:
        clean = self.normalize(transcript)
        normalized = clean.casefold()
        now = time.monotonic()

        with self.lock:
            previous, previous_at = self.recent.get(session_id, ("", 0.0))
            if previous == normalized and now - previous_at < 2.0:
                self.duplicates += 1
                return {
                    "accepted": False,
                    "duplicate": True,
                    "session_id": session_id,
                    "transcript": clean,
                }
            self.recent[session_id] = (normalized, now)
            self.accepted += 1

        context = voice_context_engine.build(session_id, clean, 12)
        return {
            "accepted": True,
            "duplicate": False,
            "request_id": uuid4().hex,
            "session_id": session_id,
            "source": source,
            "transcript": clean,
            "context": context,
        }

    def complete(
        self,
        session_id: str,
        transcript: str,
        response: str,
        source: str,
    ) -> dict[str, Any]:
        return voice_context_engine.remember_exchange(
            session_id,
            self.normalize(transcript),
            self.normalize(response),
            source,
        )

    def record_error(self) -> None:
        with self.lock:
            self.errors += 1

    def status(self) -> dict[str, int]:
        with self.lock:
            return {
                "accepted": self.accepted,
                "duplicates_blocked": self.duplicates,
                "errors": self.errors,
            }


universal_voice_gateway = UniversalVoiceGateway()
