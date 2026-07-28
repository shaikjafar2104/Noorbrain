"""Sprint 8.2: explainable, read-only decision recommendations."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from services.scene_intelligence import scene_engine


class DecisionEngine:
    VERSION = "8.2.0"

    @staticmethod
    def _score(scene: Dict[str, Any]) -> float:
        score = 0.15
        if scene.get("occupied"):
            score += 0.35
        count = int(scene.get("person_count") or 0)
        score += min(count, 3) * 0.10
        if scene.get("primary_zone") and scene.get("primary_zone") != "Unknown":
            score += 0.10
        if scene.get("recognized_people"):
            score += 0.10
        return round(min(score, 1.0), 2)

    def evaluate(self) -> Dict[str, Any]:
        scene = scene_engine.analyze()
        score = self._score(scene)
        reasons: List[str] = []
        action = "observe"
        priority = "low"

        if not scene.get("occupied"):
            reasons.append("No person is currently detected.")
            action = "wait"
        else:
            reasons.append(f"{scene.get('person_count', 0)} person(s) detected.")
            if scene.get("primary_zone"):
                reasons.append(f"Primary occupied zone is {scene['primary_zone']}.")
            if scene.get("recognized_people"):
                reasons.append("At least one recognized person is present.")
            action = "consider_contextual_reminder"
            priority = "medium" if score < 0.75 else "high"

        return {
            "status": "ok",
            "timestamp": time.time(),
            "decision": action,
            "priority": priority,
            "score": score,
            "explanation": " ".join(reasons),
            "reasons": reasons,
            "scene": scene,
            "automatic_action_taken": False,
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy", "service": "decision_engine", "version": self.VERSION}


decision_engine = DecisionEngine()
