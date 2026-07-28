from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .storage import JsonStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SmartHomePlanner:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.store = JsonStore(project / "data" / "sprint12_plans.json", "plans")

    def create(self, goal: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        goal_text = goal.strip()
        if not goal_text:
            raise ValueError("Goal is required.")

        context = context or {}
        actions: list[dict[str, Any]] = []

        room = context.get("room")
        device_id = context.get("device_id")

        if device_id:
            actions.append({
                "type": "device_action",
                "device_id": device_id,
                "action": context.get("action", "toggle"),
            })
        elif room:
            actions.append({
                "type": "room_review",
                "room": room,
            })
        else:
            actions.append({
                "type": "recommendation",
                "message": "Review available devices and automation rules.",
            })

        plan = {
            "id": uuid4().hex,
            "goal": goal_text,
            "context": context,
            "actions": actions,
            "status": "draft",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }

        plans = self.store.read()
        plans.append(plan)
        self.store.write(plans)
        return plan

    def list(self) -> list[dict[str, Any]]:
        return self.store.read()

    def approve(self, plan_id: str) -> dict[str, Any]:
        plans = self.store.read()
        index = next((i for i, item in enumerate(plans) if item["id"] == plan_id), None)
        if index is None:
            raise KeyError(f"Plan not found: {plan_id}")
        plans[index]["status"] = "approved"
        plans[index]["updated_at"] = utc_now()
        self.store.write(plans)
        return plans[index]


planner = SmartHomePlanner()
