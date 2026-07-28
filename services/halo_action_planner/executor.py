from __future__ import annotations

from typing import Any

from services.halo_os.registry import skill_registry


class ActionPlanExecutor:
    def execute(
        self,
        plan: dict[str, Any],
        *,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        results = []
        halted = False

        for step in plan.get("steps", []):
            if step.get("requires_confirmation") and not confirmed:
                step_result = {
                    **step,
                    "status": "needs_confirmation",
                    "result": None,
                }
                results.append(step_result)
                halted = True
                break

            try:
                result = self._execute_step(step)
                step_result = {
                    **step,
                    "status": "completed",
                    "result": result,
                }
            except Exception as exc:
                step_result = {
                    **step,
                    "status": "failed",
                    "result": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                halted = True

            results.append(step_result)

            if halted:
                break

        completed = sum(
            1 for item in results
            if item.get("status") == "completed"
        )

        return {
            "status": (
                "needs_confirmation"
                if any(item.get("status") == "needs_confirmation" for item in results)
                else "failed"
                if any(item.get("status") == "failed" for item in results)
                else "completed"
            ),
            "plan_id": plan.get("id"),
            "completed_steps": completed,
            "total_steps": len(plan.get("steps", [])),
            "results": results,
        }

    def _execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        kind = step.get("kind")

        if kind == "skill":
            return skill_registry.execute(
                str(step.get("name")),
                dict(step.get("arguments") or {}),
            )

        if kind == "device_action":
            from services.offline_agent.tool_registry import tool_registry
            from services.offline_agent import tools as _tools  # noqa: F401

            return tool_registry.execute(
                "set_device_state",
                dict(step.get("arguments") or {}),
            )

        if kind == "conversation":
            from services.halo_os.conversation import conversation_engine

            text = str((step.get("arguments") or {}).get("text") or "")
            return conversation_engine.process(
                text,
                session_id="planner",
                confirm=False,
            )

        raise ValueError(f"Unsupported plan step kind: {kind}")


action_plan_executor = ActionPlanExecutor()
