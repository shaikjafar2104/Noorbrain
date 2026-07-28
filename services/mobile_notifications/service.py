from __future__ import annotations

from datetime import datetime
from typing import Any

from .store import mobile_notification_store


class MobileNotificationService:
    def publish(
        self,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        settings = mobile_notification_store.read()[
            "settings"
        ]

        if not settings.get("enabled", True):
            return {
                "status": "disabled",
                "notification": None,
            }

        notification = (
            mobile_notification_store.create(item)
        )

        return {
            "status": "created",
            "notification": notification,
            "delivery": {
                "in_app": "ready",
                "browser_notification": (
                    "client_permission_required"
                ),
            },
        }

    def action(
        self,
        *,
        notification_id: str,
        action: str,
    ) -> dict[str, Any]:
        action = action.strip().casefold()

        changes: dict[str, Any]

        if action in {"read", "mark_read"}:
            changes = {
                "read": True,
                "status": "read",
            }
        elif action == "archive":
            changes = {
                "archived": True,
                "status": "archived",
            }
        elif action == "dismiss":
            changes = {
                "read": True,
                "archived": True,
                "status": "dismissed",
            }
        elif action in {
            "completed",
            "complete",
        }:
            changes = {
                "read": True,
                "status": "completed",
                "completed_at":
                    datetime.now()
                    .astimezone()
                    .isoformat(),
            }
        elif action == "snooze":
            changes = {
                "read": True,
                "status": "snoozed",
            }
        else:
            raise ValueError(
                f"Unsupported action: {action}"
            )

        updated = mobile_notification_store.update(
            notification_id,
            changes,
        )

        self._acknowledge_source(
            updated,
            action,
        )

        return {
            "status": "updated",
            "action": action,
            "notification": updated,
        }

    @staticmethod
    def _acknowledge_source(
        notification: dict[str, Any],
        action: str,
    ) -> None:
        metadata = dict(
            notification.get("metadata") or {}
        )
        source = metadata.get("source")
        source_id = metadata.get("source_id")

        if (
            source == "prayer_intelligence"
            and source_id
        ):
            try:
                from services.prayer_intelligence.store import (
                    prayer_store,
                )

                prayer_store.acknowledge(
                    str(
                        metadata.get("prayer")
                        or source_id
                    ),
                    str(
                        metadata.get("date")
                        or datetime.now()
                        .date()
                        .isoformat()
                    ),
                )
            except Exception:
                pass

        if source == "islamic_reminders":
            try:
                from services.islamic_reminders.store import (
                    islamic_reminder_store,
                )

                islamic_reminder_store.add_event({
                    "kind":
                        "mobile_acknowledgement",
                    "source_event_id": source_id,
                    "notification_id":
                        notification.get("id"),
                    "action": action,
                    "message":
                        notification.get("message"),
                })
            except Exception:
                pass


mobile_notification_service = (
    MobileNotificationService()
)
