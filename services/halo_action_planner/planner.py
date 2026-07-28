from __future__ import annotations

import re
from typing import Any
from uuid import uuid4


class MultiTurnActionPlanner:
    def plan(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        normalized = re.sub(r"\s+", " ", text.strip().casefold())
        steps: list[dict[str, Any]] = []

        if " and " in normalized or " aur " in normalized:
            parts = re.split(r"\s+(?:and|aur)\s+", text.strip(), flags=re.IGNORECASE)
        else:
            parts = [text.strip()]

        for part in parts:
            step = self._step_from_text(part, context)
            if step is not None:
                steps.append(step)

        if not steps:
            steps.append({
                "index": 0,
                "kind": "conversation",
                "name": "conversation",
                "arguments": {"text": text.strip()},
                "status": "pending",
                "requires_confirmation": False,
            })

        for index, step in enumerate(steps):
            step["index"] = index

        requires_confirmation = any(
            bool(step.get("requires_confirmation"))
            for step in steps
        )

        return {
            "id": uuid4().hex,
            "status": "planned",
            "original_text": text,
            "step_count": len(steps),
            "requires_confirmation": requires_confirmation,
            "steps": steps,
        }

    def _step_from_text(
        self,
        text: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        normalized = re.sub(r"\s+", " ", text.strip().casefold())

        match = re.search(
            r"(?:turn|switch)\s+(?:the\s+)?(.+?)\s+(on|off)$",
            normalized,
        )
        if match:
            return {
                "kind": "device_action",
                "name": "set_device_state",
                "arguments": {
                    "name": match.group(1).strip(),
                    "state": match.group(2),
                },
                "status": "pending",
                "requires_confirmation": True,
            }

        if normalized in {"home status", "ghar ka status", "house status"}:
            return {
                "kind": "skill",
                "name": "home",
                "arguments": {},
                "status": "pending",
                "requires_confirmation": False,
            }

        if "camera status" in normalized:
            return {
                "kind": "skill",
                "name": "camera",
                "arguments": {},
                "status": "pending",
                "requires_confirmation": False,
            }

        if "activity summary" in normalized or "recent activity" in normalized:
            return {
                "kind": "skill",
                "name": "activity",
                "arguments": {},
                "status": "pending",
                "requires_confirmation": False,
            }

        if normalized in {"and kitchen too", "kitchen too", "aur kitchen bhi"}:
            last_action = context.get("last_action")
            if isinstance(last_action, dict):
                action = last_action.get("action")
                if action in {"on", "off"}:
                    return {
                        "kind": "device_action",
                        "name": "set_device_state",
                        "arguments": {
                            "name": "Kitchen Light",
                            "state": action,
                        },
                        "status": "pending",
                        "requires_confirmation": True,
                    }

        return None


multi_turn_planner = MultiTurnActionPlanner()
