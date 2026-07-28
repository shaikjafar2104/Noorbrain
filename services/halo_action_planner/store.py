from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlanStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "halo_action_plans.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({"plans": []})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload.setdefault("plans", [])
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="halo-action-plans-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def save(self, plan: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()
        item = {
            **plan,
            "created_at": plan.get("created_at") or utc_now(),
            "updated_at": utc_now(),
        }
        payload["plans"].append(item)
        payload["plans"] = payload["plans"][-200:]
        self._write(payload)
        return item

    def list(self) -> list[dict[str, Any]]:
        payload = self._read()
        return list(reversed(payload["plans"]))

    def get(self, plan_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in self.list() if item.get("id") == plan_id),
            None,
        )

    def update_execution(
        self,
        plan_id: str,
        execution: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._read()

        for item in payload["plans"]:
            if item.get("id") == plan_id:
                item["execution"] = execution
                item["updated_at"] = utc_now()
                self._write(payload)
                return item

        raise KeyError(f"Plan not found: {plan_id}")


plan_store = PlanStore()
