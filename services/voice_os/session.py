from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceSessionManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, dict[str, Any]] = {}

    def touch(
        self,
        session_id: str,
        *,
        state: str,
        text: str | None = None,
        reply: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            current = self._sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "created_at": utc_now(),
                    "turn_count": 0,
                },
            )

            current["state"] = state
            current["updated_at"] = utc_now()

            if text is not None:
                current["last_text"] = text
                current["turn_count"] = int(current.get("turn_count", 0)) + 1

            if reply is not None:
                current["last_reply"] = reply

            return dict(current)

    def get(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            current = self._sessions.get(session_id)

            if current is None:
                return {
                    "session_id": session_id,
                    "state": "idle",
                    "turn_count": 0,
                    "updated_at": None,
                }

            return dict(current)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            items = [dict(item) for item in self._sessions.values()]

        items.sort(
            key=lambda item: item.get("updated_at") or "",
            reverse=True,
        )
        return items


voice_sessions = VoiceSessionManager()
