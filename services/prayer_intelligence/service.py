from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .calculator import PrayerSettings, calculate_prayer_times
from .store import prayer_store


class PrayerIntelligenceService:
    def settings(self) -> dict[str, Any]:
        return prayer_store.read()["settings"]

    def times_for(self, day: date) -> dict[str, Any]:
        raw = self.settings()
        settings = PrayerSettings(
            latitude=float(raw["latitude"]),
            longitude=float(raw["longitude"]),
            timezone=str(raw["timezone"]),
            fajr_angle=float(raw.get("fajr_angle", 18.0)),
            isha_angle=float(raw.get("isha_angle", 17.0)),
            asr_factor=float(raw.get("asr_factor", 1.0)),
        )
        calculated = calculate_prayer_times(day, settings)

        return {
            "date": day.isoformat(),
            "timezone": settings.timezone,
            "times": {
                name: value.isoformat()
                for name, value in calculated.items()
            },
            "friday_mode": bool(
                raw.get("friday_mode", True)
                and day.weekday() == 4
            ),
            "ramadan_mode": bool(raw.get("ramadan_mode", False)),
        }

    def status(self, now: datetime | None = None) -> dict[str, Any]:
        raw = self.settings()
        zone = ZoneInfo(str(raw["timezone"]))
        now = now.astimezone(zone) if now else datetime.now(zone)
        today = self.times_for(now.date())
        prayer_times = {
            name: datetime.fromisoformat(value)
            for name, value in today["times"].items()
        }

        ordered = [
            "fajr",
            "dhuhr",
            "asr",
            "maghrib",
            "isha",
        ]

        previous_name = None
        next_name = None

        for name in ordered:
            if prayer_times[name] <= now:
                previous_name = name
            elif next_name is None:
                next_name = name

        if next_name is None:
            tomorrow = self.times_for(now.date() + timedelta(days=1))
            next_name = "fajr"
            next_time = datetime.fromisoformat(
                tomorrow["times"]["fajr"]
            )
        else:
            next_time = prayer_times[next_name]

        previous_time = (
            prayer_times[previous_name]
            if previous_name
            else None
        )

        return {
            "status": "ok",
            "now": now.isoformat(),
            "today": today,
            "previous_prayer": previous_name,
            "previous_time": (
                previous_time.isoformat()
                if previous_time
                else None
            ),
            "next_prayer": next_name,
            "next_time": next_time.isoformat(),
            "seconds_to_next": max(
                0,
                int((next_time - now).total_seconds()),
            ),
        }

    def due_events(self, now: datetime | None = None) -> dict[str, Any]:
        raw = self.settings()
        zone = ZoneInfo(str(raw["timezone"]))
        now = now.astimezone(zone) if now else datetime.now(zone)
        status = self.status(now)
        pre_minutes = int(raw.get("pre_prayer_minutes", 10))
        due = []

        for prayer, value in status["today"]["times"].items():
            if prayer == "sunrise":
                continue

            prayer_time = datetime.fromisoformat(value)
            seconds = int((prayer_time - now).total_seconds())

            if 0 <= seconds <= 30:
                due.append({
                    "kind": "adhan",
                    "prayer": prayer,
                    "time": value,
                    "message": f"It is time for {prayer.title()} prayer.",
                })
            elif 0 < seconds <= pre_minutes * 60:
                due.append({
                    "kind": "pre_prayer",
                    "prayer": prayer,
                    "time": value,
                    "message": (
                        f"{prayer.title()} prayer is in "
                        f"{max(1, seconds // 60)} minute(s)."
                    ),
                })

        return {
            "status": "ok",
            "due_count": len(due),
            "events": due,
        }

    def speak_event(self, event: dict[str, Any]) -> dict[str, Any]:
        message = str(event.get("message") or "").strip()

        if not message:
            return {"status": "ignored"}

        try:
            from services.halo_voice_runtime.tts_service import streaming_tts_service

            item = streaming_tts_service.enqueue(
                message,
                priority=5,
                metadata={
                    "source": "prayer_intelligence",
                    "prayer": event.get("prayer"),
                    "kind": event.get("kind"),
                },
            )
            streaming_tts_service.start()
            result = {"status": "queued", "item": item}
        except Exception:
            try:
                from services.reminder_engine.reminder_engine import reminder_engine
                reminder_engine.speech_queue.put(message)
                result = {"status": "queued_legacy"}
            except Exception as exc:
                result = {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }

        prayer_store.add_event({
            **event,
            "delivery": result,
        })
        return result


prayer_intelligence_service = PrayerIntelligenceService()
