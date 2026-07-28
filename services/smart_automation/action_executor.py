from __future__ import annotations

from typing import Any

from .store import automation_store


class AutomationActionExecutor:
    def execute_actions(
        self,
        *,
        rule: dict[str, Any],
        context: dict[str, Any],
        confirmed: bool = False,
    ) -> dict[str, Any]:
        results: list[dict[str, Any]] = []

        for index, action in enumerate(list(rule.get("actions") or [])):
            safety = self._safety_check(action)

            if safety["requires_confirmation"] and not confirmed:
                results.append({
                    "index": index,
                    "status": "needs_confirmation",
                    "action": action,
                    "safety": safety,
                })
                return self._record_run(
                    rule=rule,
                    context=context,
                    status="needs_confirmation",
                    results=results,
                )

            try:
                result = self._execute_action(action, context=context)
                results.append({
                    "index": index,
                    "status": "completed",
                    "action": action,
                    "safety": safety,
                    "result": result,
                })
            except Exception as exc:
                results.append({
                    "index": index,
                    "status": "failed",
                    "action": action,
                    "safety": safety,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                return self._record_run(
                    rule=rule,
                    context=context,
                    status="failed",
                    results=results,
                )

        return self._record_run(
            rule=rule,
            context=context,
            status="completed",
            results=results,
        )

    def _execute_action(
        self,
        action: dict[str, Any],
        *,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        kind = str(action.get("kind") or "halo")
        name = str(action.get("name") or "respond")
        arguments = dict(action.get("arguments") or {})

        if kind == "halo":
            if name == "speak":
                try:
                    from services.halo_voice_runtime.tts_service import streaming_tts_service

                    item = streaming_tts_service.enqueue(
                        str(arguments.get("text") or ""),
                        priority=int(arguments.get("priority", 10)),
                        metadata={"source": "smart_automation"},
                    )
                    streaming_tts_service.start()
                    return {"status": "queued", "item": item}
                except Exception:
                    return {
                        "status": "simulated",
                        "message": str(arguments.get("text") or ""),
                    }

            from services.halo_brain.brain import halo_brain

            return halo_brain.process(
                text=str(arguments.get("text") or ""),
                session_id="smart-automation",
                person_id=context.get("person_id"),
                zone=context.get("zone"),
                confirm=True,
                metadata={"source": "smart_automation"},
            )

        if kind == "skill":
            from services.halo_os.registry import skill_registry
            return skill_registry.execute(name, arguments)

        if kind == "device":
            from services.offline_agent.tool_registry import tool_registry
            from services.offline_agent import tools as _tools  # noqa: F401

            tool_name = str(arguments.pop("tool", "set_device_state"))
            return tool_registry.execute(tool_name, arguments)

        if kind == "memory":
            from services.halo_brain.memory_engine import halo_memory_engine

            memory = halo_memory_engine.remember(
                kind=str(arguments.get("kind") or "automation_note"),
                value=arguments.get("value"),
                person_id=context.get("person_id"),
                zone=context.get("zone"),
                importance=float(arguments.get("importance", 0.7)),
                metadata={"source": "smart_automation"},
            )
            return {"status": "ok", "memory": memory}

        if kind == "webhook":
            raise RuntimeError("Webhook execution is disabled.")

        raise ValueError(f"Unsupported action kind: {kind}")

    @staticmethod
    def _safety_check(action: dict[str, Any]) -> dict[str, Any]:
        kind = str(action.get("kind") or "")
        name = str(action.get("name") or "")
        arguments = dict(action.get("arguments") or {})

        dangerous = (
            kind == "device"
            or arguments.get("destructive") is True
            or name in {
                "unlock",
                "delete",
                "erase",
                "shutdown",
                "reboot",
            }
        )

        return {
            "risk": "high" if dangerous else "low",
            "requires_confirmation": bool(
                action.get("requires_confirmation", dangerous)
            ),
        }

    @staticmethod
    def _record_run(
        *,
        rule: dict[str, Any],
        context: dict[str, Any],
        status: str,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        run = automation_store.add_run({
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "status": status,
            "context": context,
            "results": results,
        })

        if status == "completed":
            automation_store.update_rule(
                str(rule["id"]),
                {
                    "last_run_at": run["created_at"],
                    "run_count": int(rule.get("run_count", 0)) + 1,
                },
            )

        return {
            "status": status,
            "run": run,
            "results": results,
        }


automation_action_executor = AutomationActionExecutor()
