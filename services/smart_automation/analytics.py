from __future__ import annotations

from collections import Counter
from typing import Any

from .store import automation_store


class AutomationAnalytics:
    def summary(self) -> dict[str, Any]:
        rules = automation_store.list_rules()
        runs = automation_store.list_runs(limit=5000)

        by_status = Counter(
            str(run.get("status") or "unknown")
            for run in runs
        )
        by_rule = Counter(
            str(run.get("rule_name") or run.get("rule_id") or "unknown")
            for run in runs
        )

        return {
            "status": "ok",
            "rule_count": len(rules),
            "enabled_rule_count": sum(
                1 for rule in rules if rule.get("enabled", True)
            ),
            "run_count": len(runs),
            "by_status": dict(by_status.most_common()),
            "by_rule": dict(by_rule.most_common()),
        }


automation_analytics = AutomationAnalytics()
