from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .storage import JsonStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationMemoryV2:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.store = JsonStore(project / "data" / "sprint12_memory.json", "messages")

    def add(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        messages = self.store.read()
        item = {
            "id": uuid4().hex,
            "session_id": session_id,
            "role": role,
            "content": content.strip(),
            "metadata": metadata or {},
            "created_at": utc_now(),
        }
        messages.append(item)
        self.store.write(messages[-5000:])
        return item

    def history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        items = [
            item for item in self.store.read()
            if item.get("session_id") == session_id
        ]
        return items[-max(1, min(limit, 500)):]

    def sessions(self) -> list[dict[str, Any]]:
        summary: dict[str, dict[str, Any]] = {}
        for item in self.store.read():
            session_id = str(item.get("session_id"))
            row = summary.setdefault(
                session_id,
                {"session_id": session_id, "message_count": 0, "last_message_at": None},
            )
            row["message_count"] += 1
            row["last_message_at"] = item.get("created_at")
        return sorted(
            summary.values(),
            key=lambda row: row.get("last_message_at") or "",
            reverse=True,
        )

    def clear(self, session_id: str) -> int:
        items = self.store.read()
        remaining = [item for item in items if item.get("session_id") != session_id]
        removed = len(items) - len(remaining)
        self.store.write(remaining)
        return removed


memory_v2 = ConversationMemoryV2()
