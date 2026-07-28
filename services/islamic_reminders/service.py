from __future__ import annotations
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .store import islamic_reminder_store

class IslamicReminderService:
    def __init__(self) -> None:
        self.last_played: dict[str, float] = {}

    def evaluate(
        self,
        *,
        event_type: str,
        zone: str | None = None,
        person_id: str | None = None,
        timezone_name: str = "America/Toronto",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(ZoneInfo(timezone_name))
        window = self._time_window(now.hour)
        matches = []

        for mapping in islamic_reminder_store.list_mappings():
            if not mapping.get("enabled", True):
                continue

            trigger = dict(mapping.get("trigger") or {})
            if trigger.get("event_type") not in (None, event_type):
                continue

            trigger_zone = trigger.get("zone")
            if trigger_zone and str(trigger_zone).casefold() != str(zone or "").casefold():
                continue

            trigger_window = trigger.get("time_window")
            if trigger_window and trigger_window != window:
                continue

            key = f"{mapping['id']}:{person_id or 'any'}"
            cooldown = int(mapping.get("cooldown_seconds", 300))
            last = self.last_played.get(key, 0.0)

            if time.time() - last < cooldown:
                continue

            personalized = self._personalize(
                str(mapping.get("message") or ""),
                person_id=person_id,
            )

            matches.append({
                **mapping,
                "message": personalized,
                "person_id": person_id,
                "zone": zone,
                "time_window": window,
                "metadata": metadata or {},
            })

        return {
            "status": "ok",
            "matched_count": len(matches),
            "matches": matches,
        }

    def trigger(self, payload: dict[str, Any]) -> dict[str, Any]:
        evaluation = self.evaluate(
            event_type=str(payload.get("event_type") or "manual"),
            zone=payload.get("zone"),
            person_id=payload.get("person_id"),
            timezone_name=str(payload.get("timezone") or "America/Toronto"),
            metadata=dict(payload.get("metadata") or {}),
        )

        deliveries = []
        for item in evaluation["matches"]:
            delivery = self._deliver(item)
            self.last_played[
                f"{item['id']}:{item.get('person_id') or 'any'}"
            ] = time.time()

            event = islamic_reminder_store.add_event({
                "mapping_id": item["id"],
                "mapping_name": item.get("name"),
                "category": item.get("category"),
                "event_type": payload.get("event_type"),
                "zone": item.get("zone"),
                "person_id": item.get("person_id"),
                "message": item.get("message"),
                "delivery": delivery,
            })
            deliveries.append({"event": event, "delivery": delivery})

        return {
            **evaluation,
            "delivery_count": len(deliveries),
            "deliveries": deliveries,
        }

    def _deliver(self, item: dict[str, Any]) -> dict[str, Any]:
        message = str(item.get("message") or "").strip()

        try:
            from services.halo_voice_runtime.tts_service import streaming_tts_service
            queued = streaming_tts_service.enqueue(
                message,
                priority=int(item.get("priority", 5)),
                metadata={
                    "source": "islamic_reminders",
                    "category": item.get("category"),
                    "person_id": item.get("person_id"),
                    "zone": item.get("zone"),
                },
            )
            streaming_tts_service.start()
            voice = {"status": "queued", "item": queued}
        except Exception:
            try:
                from services.reminder_engine.reminder_engine import reminder_engine
                reminder_engine.speech_queue.put(message)
                voice = {"status": "queued_legacy"}
            except Exception as exc:
                voice = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

        mobile = self._mobile_event(item)

        return {
            "voice": voice,
            "mobile": mobile,
        }

    @staticmethod
    def _mobile_event(item: dict[str, Any]) -> dict[str, Any]:
        try:
            from services.mobile_companion.routes import mobile_event_store
            event = mobile_event_store.add({
                "type": "islamic_reminder",
                "title": item.get("name") or "Islamic Reminder",
                "message": item.get("message"),
                "person_id": item.get("person_id"),
                "zone": item.get("zone"),
                "category": item.get("category"),
            })
            return {"status": "created", "event": event}
        except Exception:
            return {
                "status": "available_via_api",
                "payload": {
                    "type": "islamic_reminder",
                    "title": item.get("name"),
                    "message": item.get("message"),
                },
            }

    @staticmethod
    def _personalize(message: str, person_id: str | None) -> str:
        if not person_id:
            return message

        try:
            from services.family_ai.store import family_store
            profiles = family_store.read().get("profiles", [])
            profile = next(
                (item for item in profiles if str(item.get("id")) == str(person_id)),
                None,
            )
            name = profile.get("name") if profile else None
            return f"{name}, {message}" if name else message
        except Exception:
            return message

    @staticmethod
    def _time_window(hour: int) -> str:
        if 4 <= hour < 11:
            return "morning"
        if 11 <= hour < 17:
            return "day"
        if 17 <= hour < 21:
            return "evening"
        return "night"

islamic_reminder_service = IslamicReminderService()
