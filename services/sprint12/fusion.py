from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .storage import JsonStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContextFusion:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.store = JsonStore(project / "data" / "sprint12_fusion.json", "events")

    def fuse(
        self,
        vision: dict[str, Any] | None,
        voice: dict[str, Any] | None,
        automation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        item = {
            "id": uuid4().hex,
            "vision": vision or {},
            "voice": voice or {},
            "automation": automation or {},
            "created_at": utc_now(),
        }

        confidence_parts = [
            bool(item["vision"]),
            bool(item["voice"]),
            bool(item["automation"]),
        ]
        item["confidence"] = round(sum(confidence_parts) / 3, 2)
        item["summary"] = {
            "has_vision": bool(item["vision"]),
            "has_voice": bool(item["voice"]),
            "has_automation": bool(item["automation"]),
        }

        events = self.store.read()
        events.append(item)
        self.store.write(events[-2000:])
        return item

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.read()[-max(1, min(limit, 500)):]


fusion_engine = ContextFusion()
