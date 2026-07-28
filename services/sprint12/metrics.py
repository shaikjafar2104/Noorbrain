from __future__ import annotations

from pathlib import Path
from typing import Any

from .fusion import fusion_engine
from .memory_v2 import memory_v2
from .planner import planner
from .skills import skill_engine


class Sprint12Metrics:
    def snapshot(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "memory_messages": len(memory_v2.store.read()),
            "memory_sessions": len(memory_v2.sessions()),
            "skills": len(skill_engine.list()),
            "plans": len(planner.list()),
            "fusion_events": len(fusion_engine.store.read()),
        }


metrics = Sprint12Metrics()
