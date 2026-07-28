from __future__ import annotations

from typing import Any, Callable


class SkillEngine:
    def __init__(self) -> None:
        self._skills: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self.register("echo", self._echo)
        self.register("device_summary", self._device_summary)
        self.register("automation_summary", self._automation_summary)

    def register(
        self,
        name: str,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._skills[name] = handler

    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "enabled": True}
            for name in sorted(self._skills)
        ]

    def execute(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        handler = self._skills.get(name)
        if handler is None:
            raise KeyError(f"Skill not found: {name}")
        return handler(payload)

    @staticmethod
    def _echo(payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "echo": payload}

    @staticmethod
    def _device_summary(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from services.automation.manager import device_manager
            return {"status": "ok", "summary": device_manager.stats()}
        except Exception as exc:
            return {"status": "degraded", "reason": str(exc)}

    @staticmethod
    def _automation_summary(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from services.automation.diagnostics import automation_diagnostics
            return {"status": "ok", "summary": automation_diagnostics.snapshot()}
        except Exception as exc:
            return {"status": "degraded", "reason": str(exc)}


skill_engine = SkillEngine()
