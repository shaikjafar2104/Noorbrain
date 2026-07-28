from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .condition_engine import condition_engine
from .context_provider import automation_context_provider
from .scheduler import scheduler
from .store import automation_store


class AutomationRuleEngine:
    def evaluate_rule(
        self,
        rule: dict[str, Any],
        *,
        context: dict[str, Any],
        force: bool = False,
    ) -> dict[str, Any]:
        if not rule.get("enabled", True):
            return {
                "matched": False,
                "reason": "disabled",
                "conditions": [],
            }

        if not force:
            schedule = dict(rule.get("schedule") or {"kind": "manual"})
            schedule["last_run_at"] = rule.get("last_run_at")

            if schedule.get("kind") != "manual" and not scheduler.due(schedule):
                return {
                    "matched": False,
                    "reason": "not_due",
                    "conditions": [],
                }

        results = [
            condition_engine.evaluate(condition, context)
            for condition in list(rule.get("conditions") or [])
        ]

        mode = str(rule.get("condition_mode") or "all")
        matched = (
            all(result["matched"] for result in results)
            if mode == "all"
            else any(result["matched"] for result in results)
        )

        if not results:
            matched = True

        return {
            "matched": matched,
            "reason": "conditions_met" if matched else "conditions_failed",
            "conditions": results,
        }

    def evaluate_all(
        self,
        *,
        event_type: str | None = None,
        person_id: str | None = None,
        zone: str | None = None,
        metadata: dict[str, Any] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        context = automation_context_provider.snapshot(
            event_type=event_type,
            person_id=person_id,
            zone=zone,
            metadata=metadata,
        )

        matches = []

        for rule in automation_store.list_rules():
            result = self.evaluate_rule(
                rule,
                context=context,
                force=force,
            )

            if result["matched"]:
                matches.append({
                    "rule": rule,
                    "evaluation": result,
                })

        return {
            "status": "ok",
            "matched_count": len(matches),
            "matches": matches,
            "context": context,
        }

automation_rule_engine = AutomationRuleEngine()
