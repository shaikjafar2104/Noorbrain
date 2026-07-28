from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from .store import mobile_notification_store


class NotificationDNDService:
    def status(
        self,
        *,
        now: datetime | None = None,
        timezone_name: str | None = None,
    ) -> dict[str, Any]:
        data = mobile_notification_store.read()
        settings = data["settings"]

        timezone_name = (
            timezone_name
            or settings.get("timezone")
            or "America/Toronto"
        )

        zone = ZoneInfo(str(timezone_name))
        now = now.astimezone(zone) if now else datetime.now(zone)

        enabled = bool(
            settings.get("dnd_enabled", False)
        )
        start = self._parse_time(
            str(settings.get("dnd_start", "22:00"))
        )
        end = self._parse_time(
            str(settings.get("dnd_end", "06:00"))
        )

        active = (
            enabled
            and self._inside(
                now.time().replace(tzinfo=None),
                start,
                end,
            )
        )

        return {
            "status": "ok",
            "enabled": enabled,
            "active": active,
            "now": now.isoformat(),
            "timezone": timezone_name,
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
        }

    def filter_delivery(
        self,
        notification: dict[str, Any],
    ) -> dict[str, Any]:
        state = self.status()
        priority = str(
            notification.get("priority")
            or "normal"
        ).casefold()

        bypass = (
            priority in {"critical", "emergency"}
            or bool(
                notification.get("bypass_dnd", False)
            )
        )

        muted = state["active"] and not bypass

        return {
            "status": "muted" if muted else "allowed",
            "muted": muted,
            "bypass": bypass,
            "dnd": state,
        }

    @staticmethod
    def _parse_time(value: str) -> time:
        hour, minute = value.split(":", 1)
        return time(
            hour=int(hour),
            minute=int(minute),
        )

    @staticmethod
    def _inside(
        current: time,
        start: time,
        end: time,
    ) -> bool:
        if start == end:
            return True

        if start < end:
            return start <= current < end

        return (
            current >= start
            or current < end
        )


notification_dnd_service = NotificationDNDService()
