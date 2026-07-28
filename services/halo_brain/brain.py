from __future__ import annotations

from typing import Any

from .decision_engine import halo_decision_engine
from .executor import halo_brain_executor
from .store import halo_brain_store


class HALOBrain:
    def process(
        self,
        *,
        text: str,
        session_id: str,
        person_id: str | None,
        zone: str | None,
        confirm: bool,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        decision_result = halo_decision_engine.decide(
            signal=text,
            person_id=person_id,
            zone=zone,
            metadata=metadata,
        )
        decision = decision_result["decision"]

        execution = halo_brain_executor.execute(
            decision,
            confirmed=confirm,
            session_id=session_id,
            person_id=person_id,
            zone=zone,
        )

        return {
            "status": execution["status"],
            "reply": execution.get("reply"),
            "decision": decision,
            "execution": execution,
            "context": decision_result.get("context"),
            "memories": decision_result.get("memories"),
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": "halo_brain",
            "version": "3.8-d2-halves1-2",
            "features": [
                "memory_engine",
                "context_fusion",
                "decision_engine",
                "skill_execution",
                "action_planner_bridge",
                "proactive_engine",
                "brain_dashboard",
            ],
            **halo_brain_store.summary(),
        }


halo_brain = HALOBrain()
