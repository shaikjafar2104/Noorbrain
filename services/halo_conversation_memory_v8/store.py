from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ConversationMemoryStore:
    def __init__(self) -> None:
        self.path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "halo_conversation_memory_v8.json"
        )
        self.lock = threading.RLock()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "8.4.0",
            "sessions": {},
            "updated_at": self.now(),
        }

    def read(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.is_file():
                return self.default()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return self.default()
            if not isinstance(data.get("sessions"), dict):
                data["sessions"] = {}
            return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = self.now()
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)

    def remember(
        self,
        session_id: str,
        role: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            session = data["sessions"].setdefault(
                session_id,
                {
                    "id": session_id,
                    "created_at": self.now(),
                    "messages": [],
                    "facts": {},
                },
            )
            message = {
                "id": uuid4().hex,
                "role": role,
                "text": text,
                "metadata": metadata or {},
                "created_at": self.now(),
            }
            session["messages"].append(message)
            session["messages"] = session["messages"][-200:]
            session["updated_at"] = self.now()
            self.write(data)
            return message

    def set_fact(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            session = data["sessions"].setdefault(
                session_id,
                {
                    "id": session_id,
                    "created_at": self.now(),
                    "messages": [],
                    "facts": {},
                },
            )
            session.setdefault("facts", {})[key] = value
            session["updated_at"] = self.now()
            self.write(data)
            return session["facts"]

    def context(self, session_id: str, limit: int = 20) -> dict[str, Any]:
        data = self.read()
        session = data["sessions"].get(session_id)
        if session is None:
            return {
                "id": session_id,
                "messages": [],
                "facts": {},
            }
        result = dict(session)
        result["messages"] = list(session.get("messages", []))[-limit:]
        return result

    def clear(self, session_id: str) -> bool:
        with self.lock:
            data = self.read()
            removed = data["sessions"].pop(session_id, None) is not None
            if removed:
                self.write(data)
            return removed


conversation_memory_store = ConversationMemoryStore()
