from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from .scene_manager import scene_manager


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RoutineScheduler:
    def __init__(self, path: Path | None = None) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = path or project / "data" / "automation_routines.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({"schema_version": 1, "routines": []})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="routines-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def list(self) -> list[dict[str, Any]]:
        return list(self._read().get("routines", []))

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        scene_id = str(payload.get("scene_id") or "").strip()
        schedule = str(payload.get("schedule") or "").strip()

        if not name:
            raise ValueError("Routine name is required.")
        if not scene_id:
            raise ValueError("scene_id is required.")
        if not schedule:
            raise ValueError("schedule is required.")

        if scene_manager.get(scene_id) is None:
            raise ValueError(f"Scene not found: {scene_id}")

        now = utc_now()
        routine = {
            "id": uuid4().hex,
            "name": name,
            "scene_id": scene_id,
            "schedule": schedule,
            "enabled": bool(payload.get("enabled", True)),
            "days": list(payload.get("days") or []),
            "created_at": now,
            "updated_at": now,
            "last_run_at": None,
            "run_count": 0,
        }

        routines = self.list()
        routines.append(routine)
        self._write({"schema_version": 1, "updated_at": now, "routines": routines})
        return routine

    def update(self, routine_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        routines = self.list()
        index = next((i for i, item in enumerate(routines) if item["id"] == routine_id), None)
        if index is None:
            raise KeyError(f"Routine not found: {routine_id}")

        protected = {"id", "created_at", "run_count", "last_run_at"}
        for key, value in patch.items():
            if key not in protected:
                routines[index][key] = value

        routines[index]["updated_at"] = utc_now()
        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "routines": routines,
        })
        return routines[index]

    def delete(self, routine_id: str) -> bool:
        routines = self.list()
        remaining = [item for item in routines if item["id"] != routine_id]
        if len(remaining) == len(routines):
            return False

        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "routines": remaining,
        })
        return True

    def run_now(self, routine_id: str) -> dict[str, Any]:
        routines = self.list()
        index = next((i for i, item in enumerate(routines) if item["id"] == routine_id), None)
        if index is None:
            raise KeyError(f"Routine not found: {routine_id}")

        routine = routines[index]
        if not routine.get("enabled", True):
            raise ValueError("Routine is disabled.")

        result = scene_manager.execute(routine["scene_id"])
        now = utc_now()
        routine["last_run_at"] = now
        routine["run_count"] = int(routine.get("run_count", 0)) + 1
        routine["updated_at"] = now
        routines[index] = routine

        self._write({
            "schema_version": 1,
            "updated_at": now,
            "routines": routines,
        })

        return {
            "status": "ok",
            "routine": routine,
            "scene_result": result,
        }


routine_scheduler = RoutineScheduler()
