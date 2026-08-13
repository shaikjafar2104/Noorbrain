from __future__ import annotations

from typing import Any

from .acknowledgements import (
    notification_acknowledgement_service,
)
from .dnd import notification_dnd_service
from .store import mobile_notification_store


class MobileNotificationFinalService:
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

        delivery = (
            notification_dnd_service.filter_delivery(
                item
            )
        )

        notification = (
            mobile_notification_store.create({
                **item,
                "delivery_state":
                    delivery["status"],
                "muted_by_dnd":
                    delivery["muted"],
            })
        )

        return {
            "status": "created",
            "notification": notification,
            "delivery": {
                **delivery,
                "in_app": "ready",
                "browser_notification": (
                    "muted"
                    if delivery["muted"]
                    else "client_permission_required"
                ),
            },
        }

    def system_status(self) -> dict[str, Any]:
        # Recovery v1: read the notification store once instead of re-reading
        # the same JSON file for summary + a 5000-item list on every status poll.
        payload = mobile_notification_store.read()
        items = payload.get("notifications", [])
        settings = payload.get("settings", {})

        by_category: dict[str, int] = {}
        unread_count = 0
        archived_count = 0
        snoozed_count = 0

        for item in items:
            category = str(item.get("category") or "general")
            by_category[category] = by_category.get(category, 0) + 1
            archived = bool(item.get("archived"))
            if archived:
                archived_count += 1
            elif not item.get("read"):
                unread_count += 1
            if item.get("status") == "snoozed":
                snoozed_count += 1

        summary = {
            "status": "ok",
            "total_count": len(items),
            "unread_count": unread_count,
            "archived_count": archived_count,
            "by_category": by_category,
            "settings": settings,
        }
        dnd = notification_dnd_service.status()

        return {
            "status": "ok",
            "version": "1.1.1-recovery",
            "summary": summary,
            "dnd": dnd,
            "snoozed_count": snoozed_count,
            "features": [
                "acknowledgements",
                "snooze_reactivation",
                "dnd_enforcement",
                "prayer_sync",
                "islamic_reminder_sync",
                "halo_memory_sync",
                "mobile_dashboard",
                "desktop_dashboard",
            ],
        }


mobile_notification_final_service = (
    MobileNotificationFinalService()
)
