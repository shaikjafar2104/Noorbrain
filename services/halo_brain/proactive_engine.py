from __future__ import annotations

from typing import Any

from .context_fusion import context_fusion
from .store import halo_brain_store


class ProactiveEngine:
    def evaluate(self) -> dict[str, Any]:
        context = context_fusion.snapshot()
        suggestions: list[dict[str, Any]] = []

        presence = context.get("presence", {}) or {}
        activity = context.get("activity", {}) or {}
        vision = context.get("vision", {}) or {}

        if presence.get("active_count", 0) > 0:
            suggestions.append({
                "kind": "presence",
                "priority": 0.4,
                "message": f"{presence.get('active_count')} person(s) currently present.",
            })

        if activity.get("total_events", 0) == 0:
            suggestions.append({
                "kind": "activity",
                "priority": 0.2,
                "message": "No activity events recorded today.",
            })

        if vision.get("status") == "degraded":
            suggestions.append({
                "kind": "vision",
                "priority": 0.9,
                "message": "Vision Intelligence is degraded.",
            })

        signal = halo_brain_store.add("signals", {
            "kind": "proactive_evaluation",
            "suggestion_count": len(suggestions),
            "suggestions": suggestions,
        })

        return {
            "status": "ok",
            "suggestion_count": len(suggestions),
            "suggestions": sorted(
                suggestions,
                key=lambda item: float(item.get("priority", 0)),
                reverse=True,
            ),
            "signal": signal,
        }


proactive_engine = ProactiveEngine()
