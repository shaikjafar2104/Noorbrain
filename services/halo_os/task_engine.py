from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.sprint12.storage import JsonStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskEngine:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.store = JsonStore(
            project / "data" / "halo_tasks.json",
            "tasks",
        )

    def create(
        self,
        title: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("Task title is required.")
        if not steps:
            raise ValueError("At least one task step is required.")

        task = {
            "id": uuid4().hex,
            "title": title.strip(),
            "status": "pending",
            "steps": [
                {
                    "index": index,
                    "status": "pending",
                    **step,
                }
                for index, step in enumerate(steps)
            ],
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }

        tasks = self.store.read()
        tasks.append(task)
        self.store.write(tasks)
        return task

    def list(self) -> list[dict[str, Any]]:
        return self.store.read()

    def get(self, task_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in self.list() if item["id"] == task_id),
            None,
        )

    def update_status(
        self,
        task_id: str,
        status: str,
    ) -> dict[str, Any]:
        tasks = self.list()
        index = next(
            (i for i, item in enumerate(tasks) if item["id"] == task_id),
            None,
        )
        if index is None:
            raise KeyError(f"Task not found: {task_id}")

        tasks[index]["status"] = status
        tasks[index]["updated_at"] = utc_now()
        self.store.write(tasks)
        return tasks[index]


task_engine = TaskEngine()
