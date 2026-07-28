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
        summary = mobile_notification_store.summary()
        dnd = notification_dnd_service.status()
        snoozed = [
            item
            for item in mobile_notification_store.list(
                limit=5000,
                include_archived=True,
            )
            if item.get("status") == "snoozed"
        ]

        return {
            "status": "ok",
            "version": "1.1.0",
            "summary": summary,
            "dnd": dnd,
            "snoozed_count": len(snoozed),
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
