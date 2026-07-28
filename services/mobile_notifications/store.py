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


class MobileNotificationStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "mobile_notifications.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

        if not self.path.exists():
            self.write({
                "settings": {
                    "enabled": True,
                    "dnd_enabled": False,
                    "dnd_start": "22:00",
                    "dnd_end": "06:00",
                    "max_notifications": 5000,
                },
                "notifications": [],
            })

    def read(self) -> dict[str, Any]:
        with self.lock:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )

        payload.setdefault("settings", {})
        payload.setdefault("notifications", [])
        return payload

    def write(self, payload: dict[str, Any]) -> None:
        with self.lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="mobile-notifications-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )

            try:
                with os.fdopen(
                    fd,
                    "w",
                    encoding="utf-8",
                ) as handle:
                    json.dump(
                        payload,
                        handle,
                        indent=2,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def create(
        self,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self.read()
        settings = payload["settings"]

        notification = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "category": "general",
            "title": "NoorBrain",
            "message": "",
            "priority": "normal",
            "read": False,
            "archived": False,
            "status": "new",
            "actions": [],
            "metadata": {},
            **item,
        }

        payload["notifications"].append(notification)

        maximum = max(
            100,
            int(settings.get("max_notifications", 5000)),
        )
        payload["notifications"] = payload[
            "notifications"
        ][-maximum:]

        self.write(payload)
        return notification

    def list(
        self,
        *,
        limit: int = 100,
        category: str | None = None,
        unread_only: bool = False,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        items = list(
            reversed(
                self.read()["notifications"]
            )
        )

        result = []

        for item in items:
            if (
                category
                and str(item.get("category") or "").casefold()
                != category.casefold()
            ):
                continue

            if unread_only and item.get("read"):
                continue

            if (
                not include_archived
                and item.get("archived")
            ):
                continue

            result.append(item)

            if len(result) >= limit:
                break

        return result

    def get(
        self,
        notification_id: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.read()["notifications"]
                if str(item.get("id"))
                == str(notification_id)
            ),
            None,
        )

    def update(
        self,
        notification_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self.read()

        for item in payload["notifications"]:
            if (
                str(item.get("id"))
                == str(notification_id)
            ):
                item.update(changes)
                item["updated_at"] = utc_now()
                self.write(payload)
                return item

        raise KeyError("Notification not found.")

    def mark_all_read(self) -> int:
        payload = self.read()
        updated = 0

        for item in payload["notifications"]:
            if not item.get("read"):
                item["read"] = True
                item["updated_at"] = utc_now()
                updated += 1

        self.write(payload)
        return updated

    def delete(
        self,
        notification_id: str,
    ) -> int:
        payload = self.read()
        before = len(payload["notifications"])

        payload["notifications"] = [
            item
            for item in payload["notifications"]
            if str(item.get("id"))
            != str(notification_id)
        ]

        removed = (
            before
            - len(payload["notifications"])
        )
        self.write(payload)
        return removed

    def clear_archived(self) -> int:
        payload = self.read()
        before = len(payload["notifications"])

        payload["notifications"] = [
            item
            for item in payload["notifications"]
            if not item.get("archived")
        ]

        removed = (
            before
            - len(payload["notifications"])
        )
        self.write(payload)
        return removed

    def update_settings(
        self,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self.read()
        payload["settings"] = {
            **payload["settings"],
            **changes,
        }
        self.write(payload)
        return payload["settings"]

    def summary(self) -> dict[str, Any]:
        payload = self.read()
        items = payload["notifications"]

        by_category: dict[str, int] = {}

        for item in items:
            category = str(
                item.get("category") or "general"
            )
            by_category[category] = (
                by_category.get(category, 0) + 1
            )

        return {
            "status": "ok",
            "total_count": len(items),
            "unread_count": sum(
                1
                for item in items
                if not item.get("read")
                and not item.get("archived")
            ),
            "archived_count": sum(
                1
                for item in items
                if item.get("archived")
            ),
            "by_category": by_category,
            "settings": payload["settings"],
        }


mobile_notification_store = MobileNotificationStore()
