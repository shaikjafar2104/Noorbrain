from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

class ConditionEngine:
    def evaluate(
        self,
        condition: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        kind = str(condition.get("kind") or "always")
        operator = str(condition.get("operator") or "eq")
        expected = condition.get("value")

        if kind == "always":
            return {"matched": True, "actual": True}

        if kind == "time_hour":
            actual = datetime.now(timezone.utc).hour
        elif kind == "zone":
            actual = context.get("zone")
        elif kind == "person_id":
            actual = context.get("person_id")
        elif kind == "presence_count":
            actual = (
                context.get("presence", {}).get("active_count", 0)
            )
        elif kind == "vision_status":
            actual = context.get("vision", {}).get("status")
        elif kind == "event_type":
            actual = context.get("event_type")
        else:
            actual = context.get(kind)

        matched = self._compare(actual, expected, operator)
        return {
            "matched": matched,
            "actual": actual,
            "expected": expected,
            "operator": operator,
        }

    @staticmethod
    def _compare(actual: Any, expected: Any, operator: str) -> bool:
        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "gt":
            return float(actual) > float(expected)
        if operator == "gte":
            return float(actual) >= float(expected)
        if operator == "lt":
            return float(actual) < float(expected)
        if operator == "lte":
            return float(actual) <= float(expected)
        if operator == "contains":
            return str(expected).casefold() in str(actual).casefold()
        if operator == "in":
            return actual in list(expected or [])
        raise ValueError(f"Unsupported operator: {operator}")

condition_engine = ConditionEngine()
