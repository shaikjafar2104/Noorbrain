from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .store import mobile_notification_store


class NotificationAcknowledgementService:
    def acknowledge(
        self,
        *,
        notification_id: str,
        action: str,
        snooze_minutes: int = 10,
        note: str | None = None,
    ) -> dict[str, Any]:
        notification = mobile_notification_store.get(
            notification_id
        )

        if notification is None:
            raise KeyError("Notification not found.")

        normalized = action.strip().casefold()
        now = datetime.now(timezone.utc)

        changes: dict[str, Any] = {
            "read": True,
            "acknowledged_at": now.isoformat(),
            "acknowledgement_note": note,
        }

        if normalized in {"complete", "completed"}:
            changes.update({
                "status": "completed",
                "completed_at": now.isoformat(),
                "archived": False,
            })
        elif normalized == "dismiss":
            changes.update({
                "status": "dismissed",
                "archived": True,
            })
        elif normalized == "skip":
            changes.update({
                "status": "skipped",
                "archived": True,
            })
        elif normalized == "snooze":
            minutes = max(1, min(int(snooze_minutes), 1440))
            changes.update({
                "status": "snoozed",
                "archived": False,
                "snoozed_until": (
                    now + timedelta(minutes=minutes)
                ).isoformat(),
            })
        elif normalized in {"read", "mark_read"}:
            changes.update({
                "status": "read",
            })
        else:
            raise ValueError(
                f"Unsupported acknowledgement action: {action}"
            )

        updated = mobile_notification_store.update(
            notification_id,
            changes,
        )

        self._sync_source(
            notification=updated,
            action=normalized,
        )

        self._remember_acknowledgement(
            notification=updated,
            action=normalized,
        )

        return {
            "status": "acknowledged",
            "action": normalized,
            "notification": updated,
        }

    def due_snoozed(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        items = mobile_notification_store.list(
            limit=5000,
            include_archived=True,
        )
        reactivated = []

        for item in items:
            if item.get("status") != "snoozed":
                continue

            value = item.get("snoozed_until")

            if not value:
                continue

            try:
                due = datetime.fromisoformat(
                    str(value).replace("Z", "+00:00")
                )
            except Exception:
                continue

            if due > now:
                continue

            updated = mobile_notification_store.update(
                str(item["id"]),
                {
                    "status": "new",
                    "read": False,
                    "snoozed_until": None,
                    "reactivated_at": now.isoformat(),
                },
            )
            reactivated.append(updated)

        return {
            "status": "ok",
            "reactivated_count": len(reactivated),
            "notifications": reactivated,
        }

    @staticmethod
    def _sync_source(
        *,
        notification: dict[str, Any],
        action: str,
    ) -> None:
        metadata = dict(
            notification.get("metadata") or {}
        )
        source = metadata.get("source")
        source_id = metadata.get("source_id")

        if source == "prayer_intelligence":
            try:
                from services.prayer_intelligence.store import (
                    prayer_store,
                )

                prayer_store.acknowledge(
                    str(
                        metadata.get("prayer")
                        or source_id
                        or "prayer"
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
                    "kind": "acknowledgement",
                    "source_event_id": source_id,
                    "notification_id": notification.get("id"),
                    "action": action,
                    "message": notification.get("message"),
                })
            except Exception:
                pass

        if source == "personalized_halo":
            try:
                from services.personalized_halo.store import (
                    personalized_halo_store,
                )

                personalized_halo_store.record_greeting(
                    profile_id=str(
                        notification.get("profile_id")
                        or "unknown"
                    ),
                    greeting={
                        "kind": "mobile_acknowledgement",
                        "notification_id":
                            notification.get("id"),
                        "action": action,
                        "message":
                            notification.get("message"),
                    },
                )
            except Exception:
                pass

    @staticmethod
    def _remember_acknowledgement(
        *,
        notification: dict[str, Any],
        action: str,
    ) -> None:
        try:
            from services.halo_brain.memory_engine import (
                halo_memory_engine,
            )

            halo_memory_engine.remember(
                kind="mobile_acknowledgement",
                value={
                    "notification_id":
                        notification.get("id"),
                    "title":
                        notification.get("title"),
                    "action": action,
                },
                person_id=notification.get("person_id"),
                zone=notification.get("zone"),
                importance=0.4,
                metadata={
                    "category":
                        notification.get("category"),
                    "profile_id":
                        notification.get("profile_id"),
                },
            )
        except Exception:
            pass


notification_acknowledgement_service = (
    NotificationAcknowledgementService()
)
