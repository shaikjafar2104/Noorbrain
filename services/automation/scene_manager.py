from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from .manager import device_manager


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SceneManager:
    def __init__(self, path: Path | None = None) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = path or project / "data" / "automation_scenes.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({"schema_version": 1, "scenes": []})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="scenes-",
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
        return list(self._read().get("scenes", []))

    def get(self, scene_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list() if item["id"] == scene_id), None)

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        actions = payload.get("actions")

        if not name:
            raise ValueError("Scene name is required.")
        if not isinstance(actions, list) or not actions:
            raise ValueError("Scene actions must be a non-empty list.")

        now = utc_now()
        scene = {
            "id": uuid4().hex,
            "name": name,
            "description": str(payload.get("description") or ""),
            "enabled": bool(payload.get("enabled", True)),
            "actions": actions,
            "created_at": now,
            "updated_at": now,
            "last_run_at": None,
            "run_count": 0,
        }

        scenes = self.list()
        scenes.append(scene)
        self._write({"schema_version": 1, "updated_at": now, "scenes": scenes})
        return scene

    def update(self, scene_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        scenes = self.list()
        index = next((i for i, item in enumerate(scenes) if item["id"] == scene_id), None)
        if index is None:
            raise KeyError(f"Scene not found: {scene_id}")

        protected = {"id", "created_at", "run_count", "last_run_at"}
        for key, value in patch.items():
            if key not in protected:
                scenes[index][key] = value

        scenes[index]["updated_at"] = utc_now()
        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "scenes": scenes,
        })
        return scenes[index]

    def delete(self, scene_id: str) -> bool:
        scenes = self.list()
        remaining = [item for item in scenes if item["id"] != scene_id]
        if len(remaining) == len(scenes):
            return False

        self._write({
            "schema_version": 1,
            "updated_at": utc_now(),
            "scenes": remaining,
        })
        return True

    def execute(self, scene_id: str) -> dict[str, Any]:
        scenes = self.list()
        index = next((i for i, item in enumerate(scenes) if item["id"] == scene_id), None)
        if index is None:
            raise KeyError(f"Scene not found: {scene_id}")

        scene = scenes[index]
        if not scene.get("enabled", True):
            raise ValueError("Scene is disabled.")

        results: list[dict[str, Any]] = []

        for action in scene.get("actions", []):
            action_type = str(action.get("type") or "")
            device_id = str(action.get("device_id") or "")

            try:
                if action_type == "device_on":
                    device = device_manager.set_state(device_id, "on")
                elif action_type == "device_off":
                    device = device_manager.set_state(device_id, "off")
                elif action_type == "device_toggle":
                    device = device_manager.toggle(device_id)
                else:
                    results.append({
                        "status": "skipped",
                        "action": action,
                        "reason": f"Unsupported action type: {action_type}",
                    })
                    continue

                results.append({
                    "status": "ok",
                    "action": action,
                    "device": device.model_dump(mode="json"),
                })
            except Exception as exc:
                results.append({
                    "status": "error",
                    "action": action,
                    "reason": str(exc),
                })

        now = utc_now()
        scene["last_run_at"] = now
        scene["run_count"] = int(scene.get("run_count", 0)) + 1
        scene["updated_at"] = now
        scenes[index] = scene
        self._write({"schema_version": 1, "updated_at": now, "scenes": scenes})

        return {
            "status": "ok",
            "scene": scene,
            "results": results,
            "success_count": sum(1 for item in results if item["status"] == "ok"),
            "error_count": sum(1 for item in results if item["status"] == "error"),
        }


scene_manager = SceneManager()
