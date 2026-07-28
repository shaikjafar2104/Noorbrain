from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationSessionManager:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "halo_conversations.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({"schema_version": 1, "sessions": {}})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))

        if not isinstance(payload, dict):
            raise RuntimeError("Conversation store must be a JSON object.")

        payload.setdefault("schema_version", 1)
        payload.setdefault("sessions", {})
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="halo-conversation-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def ensure(self, session_id: str) -> dict[str, Any]:
        payload = self._read()
        sessions = payload["sessions"]

        if session_id not in sessions:
            sessions[session_id] = {
                "id": session_id,
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "turns": [],
                "context": {},
                "pending_clarification": None,
                "status": "active",
            }
            self._write(payload)

        return dict(sessions[session_id])

    def append_turn(
        self,
        session_id: str,
        *,
        role: str,
        text: str,
        intent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._read()
        sessions = payload["sessions"]
        session = sessions.get(session_id)

        if session is None:
            session = self.ensure(session_id)
            payload = self._read()
            sessions = payload["sessions"]
            session = sessions[session_id]

        turn = {
            "id": uuid4().hex,
            "role": role,
            "text": text,
            "intent": intent,
            "metadata": metadata or {},
            "timestamp": utc_now(),
        }

        session["turns"].append(turn)
        session["updated_at"] = utc_now()
        session["turns"] = session["turns"][-100:]
        self._write(payload)
        return turn

    def update_context(
        self,
        session_id: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._read()
        sessions = payload["sessions"]

        if session_id not in sessions:
            self.ensure(session_id)
            payload = self._read()
            sessions = payload["sessions"]

        context = dict(sessions[session_id].get("context") or {})
        context.update(values)
        sessions[session_id]["context"] = context
        sessions[session_id]["updated_at"] = utc_now()
        self._write(payload)
        return context

    def set_clarification(
        self,
        session_id: str,
        clarification: dict[str, Any] | None,
    ) -> None:
        payload = self._read()
        sessions = payload["sessions"]

        if session_id not in sessions:
            self.ensure(session_id)
            payload = self._read()
            sessions = payload["sessions"]

        sessions[session_id]["pending_clarification"] = clarification
        sessions[session_id]["updated_at"] = utc_now()
        self._write(payload)

    def get(self, session_id: str) -> dict[str, Any]:
        payload = self._read()
        session = payload["sessions"].get(session_id)

        if session is None:
            return self.ensure(session_id)

        return dict(session)

    def list(self) -> list[dict[str, Any]]:
        payload = self._read()
        items = []

        for session in payload["sessions"].values():
            items.append({
                "id": session["id"],
                "status": session.get("status", "active"),
                "turn_count": len(session.get("turns", [])),
                "updated_at": session.get("updated_at"),
                "pending_clarification": session.get("pending_clarification"),
            })

        items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return items

    def clear(self, session_id: str) -> int:
        payload = self._read()
        removed = 1 if payload["sessions"].pop(session_id, None) is not None else 0
        self._write(payload)
        return removed


conversation_sessions = ConversationSessionManager()
