from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceQueue:
    def __init__(self) -> None:
        self._lock = RLock()
        self._items: list[dict[str, Any]] = []

    def add(
        self,
        text: str,
        *,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "text": text.strip(),
            "priority": int(priority),
            "status": "queued",
            "metadata": metadata or {},
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }

        with self._lock:
            self._items.append(item)
            self._items.sort(
                key=lambda value: (
                    -int(value.get("priority", 0)),
                    value.get("created_at", ""),
                )
            )

        return dict(item)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._items]

    def next(self) -> dict[str, Any] | None:
        with self._lock:
            item = next(
                (
                    value
                    for value in self._items
                    if value.get("status") == "queued"
                ),
                None,
            )

            if item is None:
                return None

            item["status"] = "speaking"
            item["updated_at"] = utc_now()
            return dict(item)

    def complete(self, item_id: str) -> dict[str, Any]:
        with self._lock:
            item = next(
                (value for value in self._items if value.get("id") == item_id),
                None,
            )

            if item is None:
                raise KeyError(f"Queue item not found: {item_id}")

            item["status"] = "done"
            item["updated_at"] = utc_now()
            return dict(item)

    def cancel_all(self) -> int:
        count = 0

        with self._lock:
            for item in self._items:
                if item.get("status") in {"queued", "speaking"}:
                    item["status"] = "cancelled"
                    item["updated_at"] = utc_now()
                    count += 1

        return count


voice_queue = VoiceQueue()
