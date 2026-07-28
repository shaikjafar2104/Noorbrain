from __future__ import annotations

from typing import Any

from .action_executor import automation_action_executor
from .rule_engine import automation_rule_engine


class AutomationOrchestrator:
    def evaluate_and_execute(
        self,
        *,
        event_type: str | None = None,
        person_id: str | None = None,
        zone: str | None = None,
        metadata: dict[str, Any] | None = None,
        force: bool = False,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        evaluation = automation_rule_engine.evaluate_all(
            event_type=event_type,
            person_id=person_id,
            zone=zone,
            metadata=metadata,
            force=force,
        )

        executions = []

        for match in evaluation["matches"]:
            executions.append(
                automation_action_executor.execute_actions(
                    rule=match["rule"],
                    context=evaluation["context"],
                    confirmed=confirmed,
                )
            )

        return {
            "status": "ok",
            "matched_count": evaluation["matched_count"],
            "execution_count": len(executions),
            "executions": executions,
            "context": evaluation["context"],
        }


automation_orchestrator = AutomationOrchestrator()
