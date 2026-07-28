from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class AutomationStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "smart_automation.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        if not self.path.exists():
            self.write({
                "schema_version": 1,
                "rules": [],
                "runs": [],
            })

    def read(self) -> dict[str, Any]:
        with self.lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload.setdefault("rules", [])
        payload.setdefault("runs", [])
        return payload

    def write(self, payload: dict[str, Any]) -> None:
        with self.lock:
            fd, tmp = tempfile.mkstemp(
                prefix="smart-automation-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    def create_rule(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self.read()
        rule = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "enabled": True,
            "last_run_at": None,
            "run_count": 0,
            **item,
        }
        payload["rules"].append(rule)
        self.write(payload)
        return rule

    def list_rules(self) -> list[dict[str, Any]]:
        return list(self.read()["rules"])

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        return next(
            (rule for rule in self.read()["rules"] if rule.get("id") == rule_id),
            None,
        )

    def update_rule(self, rule_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        payload = self.read()
        for rule in payload["rules"]:
            if rule.get("id") == rule_id:
                rule.update(changes)
                rule["updated_at"] = utc_now()
                self.write(payload)
                return rule
        raise KeyError("Rule not found.")

    def delete_rule(self, rule_id: str) -> int:
        payload = self.read()
        before = len(payload["rules"])
        payload["rules"] = [
            rule for rule in payload["rules"]
            if rule.get("id") != rule_id
        ]
        removed = before - len(payload["rules"])
        self.write(payload)
        return removed

    def add_run(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self.read()
        run = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            **item,
        }
        payload["runs"].append(run)
        payload["runs"] = payload["runs"][-5000:]
        self.write(payload)
        return run

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self.read()["runs"]))[:limit]

automation_store = AutomationStore()
