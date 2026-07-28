from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.family_ai.store import family_store
from services.face_identity.store import face_identity_store

from .store import personalized_halo_store


class PersonalizedHALOService:
    def profile_for_person(
        self,
        person_id: str,
    ) -> dict[str, Any] | None:
        person = face_identity_store.get_person(person_id)

        if person is None:
            return None

        profile_id = person.get("family_profile_id")

        if not profile_id:
            return None

        return next(
            (
                item
                for item in family_store.read().get("profiles", [])
                if str(item.get("id")) == str(profile_id)
            ),
            None,
        )

    def compose(
        self,
        *,
        person_id: str,
        zone: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        profile = self.profile_for_person(person_id)

        if profile is None:
            raise KeyError("Linked family profile not found.")

        now = now or datetime.now().astimezone()
        settings = personalized_halo_store.read()["settings"]
        period = self._period(
            now.hour,
            settings,
        )
        name = str(profile.get("name") or "there")
        preferences = dict(profile.get("preferences") or {})

        greeting_template = (
            preferences.get("greeting_template")
            or self._default_template(period)
        )

        greeting = str(greeting_template).format(
            name=name,
            zone=zone or "home",
            period=period,
        )

        prayer_context = self._prayer_context()

        if prayer_context:
            greeting = f"{greeting} {prayer_context}"

        reminder_context = self._reminder_context(
            profile_id=str(profile.get("id")),
        )

        if reminder_context:
            greeting = f"{greeting} {reminder_context}"

        return {
            "status": "ok",
            "person_id": person_id,
            "profile_id": profile.get("id"),
            "profile_name": name,
            "zone": zone,
            "period": period,
            "language": profile.get("language", "en"),
            "voice_profile": profile.get("voice_profile"),
            "message": greeting.strip(),
        }

    def greet(
        self,
        *,
        person_id: str,
        zone: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        data = personalized_halo_store.read()
        settings = data["settings"]

        if not settings.get("enabled", True):
            return {
                "status": "disabled",
                "person_id": person_id,
            }

        composed = self.compose(
            person_id=person_id,
            zone=zone,
        )
        profile_id = str(composed["profile_id"])

        if not force and self._cooldown_active(
            profile_id=profile_id,
            data=data,
            cooldown_seconds=int(
                settings.get("cooldown_seconds", 900)
            ),
        ):
            return {
                "status": "cooldown",
                **composed,
            }

        delivery = self._deliver(composed)

        event = personalized_halo_store.record_greeting(
            profile_id=profile_id,
            greeting={
                **composed,
                "delivery": delivery,
            },
        )

        self._remember(event)
        self._mobile(event)

        return {
            "status": "greeted",
            "greeting": event,
            "delivery": delivery,
        }

    @staticmethod
    def _period(
        hour: int,
        settings: dict[str, Any],
    ) -> str:
        morning = int(settings.get("morning_start", 4))
        afternoon = int(settings.get("afternoon_start", 12))
        evening = int(settings.get("evening_start", 17))
        night = int(settings.get("night_start", 21))

        if morning <= hour < afternoon:
            return "morning"
        if afternoon <= hour < evening:
            return "afternoon"
        if evening <= hour < night:
            return "evening"
        return "night"

    @staticmethod
    def _default_template(period: str) -> str:
        templates = {
            "morning": "Assalamu Alaikum {name}. Good morning.",
            "afternoon": "Assalamu Alaikum {name}. Good afternoon.",
            "evening": "Assalamu Alaikum {name}. Good evening.",
            "night": "Assalamu Alaikum {name}. Welcome home.",
        }
        return templates[period]

    @staticmethod
    def _cooldown_active(
        *,
        profile_id: str,
        data: dict[str, Any],
        cooldown_seconds: int,
    ) -> bool:
        value = data.get("last_greetings", {}).get(profile_id)

        if not value:
            return False

        try:
            previous = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            return (
                now - previous.astimezone(timezone.utc)
            ).total_seconds() < cooldown_seconds
        except Exception:
            return False

    @staticmethod
    def _prayer_context() -> str:
        try:
            from services.prayer_intelligence.service import (
                prayer_intelligence_service,
            )

            status = prayer_intelligence_service.status()
            name = str(status.get("next_prayer") or "").title()
            seconds = int(status.get("seconds_to_next", 0))

            if not name:
                return ""

            minutes = max(0, seconds // 60)

            if minutes <= 60:
                return (
                    f"{name} prayer is in "
                    f"{max(1, minutes)} minute(s)."
                )

            return ""
        except Exception:
            return ""

    @staticmethod
    def _reminder_context(
        *,
        profile_id: str,
    ) -> str:
        try:
            from services.islamic_reminders.store import (
                islamic_reminder_store,
            )

            recent = [
                item
                for item in islamic_reminder_store.list_events(100)
                if str(item.get("person_id") or "") == profile_id
            ]

            if recent:
                return "You have recent Islamic reminders."

            return ""
        except Exception:
            return ""

    @staticmethod
    def _deliver(
        greeting: dict[str, Any],
    ) -> dict[str, Any]:
        message = str(greeting["message"])

        try:
            from services.halo_voice_runtime.tts_service import (
                streaming_tts_service,
            )

            item = streaming_tts_service.enqueue(
                message,
                priority=8,
                metadata={
                    "source": "personalized_halo",
                    "person_id": greeting.get("person_id"),
                    "profile_id": greeting.get("profile_id"),
                    "zone": greeting.get("zone"),
                    "voice_profile": greeting.get(
                        "voice_profile"
                    ),
                },
            )
            streaming_tts_service.start()

            return {
                "status": "queued",
                "item": item,
            }
        except Exception:
            try:
                from services.reminder_engine.reminder_engine import (
                    reminder_engine,
                )

                reminder_engine.speech_queue.put(message)

                return {
                    "status": "queued_legacy",
                }
            except Exception as exc:
                return {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }

    @staticmethod
    def _remember(
        event: dict[str, Any],
    ) -> None:
        try:
            from services.halo_brain.memory_engine import (
                halo_memory_engine,
            )

            halo_memory_engine.remember(
                kind="personalized_greeting",
                value=event.get("message"),
                person_id=event.get("person_id"),
                zone=event.get("zone"),
                importance=0.5,
                metadata={
                    "profile_id": event.get("profile_id"),
                    "period": event.get("period"),
                },
            )
        except Exception:
            pass

    @staticmethod
    def _mobile(
        event: dict[str, Any],
    ) -> None:
        try:
            from services.mobile_notifications.store import (
                mobile_notification_store,
            )

            mobile_notification_store.create({
                "category": "greeting",
                "title": f"HALO greeting for {event.get('profile_name')}",
                "message": event.get("message"),
                "person_id": event.get("person_id"),
                "profile_id": event.get("profile_id"),
                "zone": event.get("zone"),
            })
        except Exception:
            pass


personalized_halo_service = PersonalizedHALOService()
