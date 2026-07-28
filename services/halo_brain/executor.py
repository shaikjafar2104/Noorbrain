from __future__ import annotations

from typing import Any

from .memory_engine import halo_memory_engine
from .store import halo_brain_store


class HALOBrainExecutor:
    def execute(
        self,
        decision: dict[str, Any],
        *,
        confirmed: bool = False,
        session_id: str = "default",
        person_id: str | None = None,
        zone: str | None = None,
    ) -> dict[str, Any]:
        action = dict(decision.get("action") or {})

        if action.get("requires_confirmation") and not confirmed:
            return {
                "status": "needs_confirmation",
                "reply": "Please confirm this action.",
                "action": action,
            }

        try:
            result = self._execute_action(
                action,
                session_id=session_id,
                person_id=person_id,
                zone=zone,
            )
            status = "completed"
        except Exception as exc:
            result = {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
            status = "failed"

        record = halo_brain_store.add("executions", {
            "decision_id": decision.get("decision_id"),
            "status": status,
            "action": action,
            "result": result,
        })

        return {
            "status": status,
            "execution": record,
            "result": result,
            "reply": self._reply_from_result(result),
        }

    def _execute_action(
        self,
        action: dict[str, Any],
        *,
        session_id: str,
        person_id: str | None,
        zone: str | None,
    ) -> dict[str, Any]:
        kind = action.get("kind")
        name = action.get("name")
        arguments = dict(action.get("arguments") or {})

        if kind == "memory" and name == "remember":
            memory = halo_memory_engine.remember(
                kind=str(arguments.get("kind") or "note"),
                value=arguments.get("value"),
                person_id=person_id,
                zone=zone,
                importance=0.8,
                metadata={"source": "halo_brain"},
            )
            return {
                "status": "ok",
                "memory": memory,
            }

        if kind == "skill":
            from services.halo_os.registry import skill_registry
            return skill_registry.execute(
                str(name),
                arguments,
            )

        if kind == "planner":
            from services.halo_action_planner.planner import multi_turn_planner
            from services.halo_action_planner.executor import action_plan_executor

            plan = multi_turn_planner.plan(
                str(arguments.get("text") or ""),
                {},
            )
            return action_plan_executor.execute(
                plan,
                confirmed=True,
            )

        from services.halo_conversation.engine import halo_conversation_engine

        return halo_conversation_engine.process(
            str(arguments.get("text") or ""),
            session_id=session_id,
            confirm=False,
        )

    @staticmethod
    def _reply_from_result(result: dict[str, Any]) -> str:
        for key in ("reply", "message", "detail"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if result.get("status") == "ok" and result.get("memory"):
            return "I will remember that."

        return "Done."


halo_brain_executor = HALOBrainExecutor()
