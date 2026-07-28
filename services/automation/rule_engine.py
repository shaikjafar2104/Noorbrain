from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuleEngine:
    def __init__(self, path: Path | None = None) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = path or project / "data" / "automation_rules.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({"schema_version": 1, "rules": []})

    def _read(self) -> dict:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="rules-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def list(self) -> list[dict[str, Any]]:
        return list(self._read().get("rules", []))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("name"):
            raise ValueError("Rule name is required.")
        if not isinstance(payload.get("trigger"), dict):
            raise ValueError("Rule trigger must be an object.")
        if not isinstance(payload.get("actions"), list) or not payload["actions"]:
            raise ValueError("Rule actions must be a non-empty list.")

        now = utc_now()
        rule = {
            "id": uuid4().hex,
            "name": str(payload["name"]),
            "enabled": bool(payload.get("enabled", True)),
            "trigger": payload["trigger"],
            "conditions": list(payload.get("conditions") or []),
            "actions": payload["actions"],
            "created_at": now,
            "updated_at": now,
            "last_triggered_at": None,
            "trigger_count": 0,
        }

        rules = self.list()
        rules.append(rule)
        self._write({
            "schema_version": 1,
            "updated_at": now,
            "rules": rules,
        })
        return rule

    def update(self, rule_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        rules = self.list()
        index = next((i for i, item in enumerate(rules) if item["id"] == rule_id), None)
        if index is None:
            raise KeyError(f"Rule not found: {rule_id}")

        protected = {"id", "created_at", "trigger_count", "last_triggered_at"}
        for key, value in patch.items():
            if key not in protected:
                rules[index][key] = value

        rules[index]["updated_at"] = utc_now()
        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "rules": rules,
        })
        return rules[index]

    def delete(self, rule_id: str) -> bool:
        rules = self.list()
        remaining = [item for item in rules if item["id"] != rule_id]
        if len(remaining) == len(rules):
            return False

        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "rules": remaining,
        })
        return True

    def evaluate(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        matches = []
        rules = self.list()

        for rule in rules:
            if not rule.get("enabled", True):
                continue

            trigger = rule.get("trigger", {})
            if all(event.get(key) == value for key, value in trigger.items()):
                matches.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "actions": rule["actions"],
                })

        return matches


rule_engine = RuleEngine()
