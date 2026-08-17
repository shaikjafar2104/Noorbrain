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
            from services.playback_router import playback_router
            settings = self.settings()
            result = playback_router.play({
                "target_node": event.get("target_node") or settings.get("playback_node"),
                "type": "media" if event.get("media_id") else "tts",
                "content": message,
                "media_id": event.get("media_id"),
                "volume": event.get("volume") or settings.get("playback_volume"),
            })
        except Exception as exc:
            result = {"status": "failed", "error": str(exc), "laptop_fallback": False}

        prayer_store.add_event({
            **event,
            "delivery": result,
        })
        return result

    # --------------------------------------------------
    # Adhan integration
    #
    # Uses Prayer Intelligence as the authoritative prayer-time source.
    # Uses Playback Router as the authoritative audio output.
    # Laptop fallback MUST remain False.
    # --------------------------------------------------

    ADHAN_MEDIA_REQUIRED = "ADHAN_MEDIA_REQUIRED"

    def _find_adhan_media_id(self) -> str | None:
        """Search the verified media catalog for an Adhan audio item.

        Only media explicitly classified as Adhan (category == "adhan")
        is accepted. Duas and Azkar that merely mention "adhan" in their
        name are NOT Adhan media.

        Returns the media_id of a verified Adhan media item, or None if
        no verified Adhan media exists.
        """
        try:
            from services.islamic_audio_rules.catalog import catalog_items
            items = catalog_items()
            for item in items:
                if item.get("category") == "adhan":
                    return str(item.get("id"))
            return None
        except Exception:
            return None

    def adhan_settings(self) -> dict[str, Any]:
        """Return Adhan-specific configuration from prayer store settings.

        Truthfully reports media availability:
        - If adhan_media_id is explicitly configured, it is only considered
          valid if the referenced catalog item has category == "adhan".
        - Otherwise, auto-discovery via _find_adhan_media_id() is used.
        - If no valid Adhan media is found, media_state is ADHAN_MEDIA_REQUIRED
          and verified_adhan_media_available is false.
        """
        raw = self.settings()
        explicit_media_id = str(raw.get("adhan_media_id") or "").strip() or None

        # Validate explicit media_id against safe contract
        media_id = explicit_media_id
        if media_id:
            media_id = self._validate_adhan_media_id(media_id)
        else:
            media_id = self._find_adhan_media_id()

        return {
            "adhan_enabled": bool(raw.get("adhan_enabled", True)),
            "adhan_target_node": str(
                raw.get("adhan_target_node") or raw.get("playback_node") or ""
            ).strip() or None,
            "adhan_lead_minutes": int(raw.get("adhan_lead_minutes", 0)),
            "adhan_media_id": media_id,
            "verified_adhan_media_available": media_id is not None,
            "media_state": (
                "verified" if media_id else self.ADHAN_MEDIA_REQUIRED
            ),
        }

    def _validate_adhan_media_id(self, media_id: str) -> str | None:
        """Validate that an explicitly configured media_id is actual Adhan media.

        A Dua/Azkar media ID must NOT become valid Adhan simply because
        it was manually placed in adhan_media_id.
        """
        try:
            from services.islamic_audio_rules.catalog import catalog_items
            items = catalog_items()
            for item in items:
                if str(item.get("id")) == str(media_id):
                    if item.get("category") == "adhan":
                        return str(item.get("id"))
                    # Explicitly configured media that is not Adhan
                    return None
            # Configured media_id not found in catalog
            return None
        except Exception:
            return None

    def check_adhan_due(
        self, now: datetime | None = None
    ) -> dict[str, Any]:
        """Check for prayer times that are due and attempt Adhan playback.

        Returns a dict with:
        - status: "played", "suppressed", "disabled", or "required"
        - events: list of prayer events that were due
        - result: playback result (if played)
        - media_state: "verified" or ADHAN_MEDIA_REQUIRED
        """
        raw = self.settings()
        adhan_cfg = self.adhan_settings()

        if not adhan_cfg["adhan_enabled"]:
            return {
                "status": "disabled",
                "events": [],
                "media_state": adhan_cfg["media_state"],
            }

        due = self.due_events(now)
        adhan_events = [
            ev for ev in due.get("events", []) if ev.get("kind") == "adhan"
        ]

        if not adhan_events:
            return {
                "status": "suppressed",
                "events": [],
                "media_state": adhan_cfg["media_state"],
            }

        # media_id is already validated in adhan_settings()
        media_id = adhan_cfg["adhan_media_id"]
        if not media_id:
            # No verified Adhan media available — return truthful state
            return {
                "status": "required",
                "events": adhan_events,
                "media_state": self.ADHAN_MEDIA_REQUIRED,
            }

        target_node = adhan_cfg["adhan_target_node"]
        if not target_node:
            return {
                "status": "required",
                "events": adhan_events,
                "media_state": adhan_cfg["media_state"],
            }

        # Deduplication: only suppress events that were SUCCESSFULLY fired.
        # Failed playback attempts must NOT prevent retries.
        already_successfully_fired = {
            (ev.get("prayer"), ev.get("time"))
            for ev in prayer_store.list_events(5000)
            if ev.get("kind") == "adhan" and ev.get("status") == "fired"
        }
        pending_events = [
            ev for ev in adhan_events
            if (ev.get("prayer"), ev.get("time")) not in already_successfully_fired
        ]

        if not pending_events:
            return {
                "status": "suppressed",
                "events": [],
                "media_state": "verified",
            }

        # Playback via authoritative Playback Router — no laptop fallback
        try:
            from services.playback_router import playback_router
            playback_result = playback_router.play({
                "target_node": target_node,
                "type": "media",
                "media_id": media_id,
            })
            played = playback_result.get("status") in {"played", "accepted", "playing"}
        except Exception as exc:
            playback_result = {
                "status": "failed",
                "error": str(exc),
                "laptop_fallback": False,
            }
            played = False

        # Record the adhan attempt.
        # Only SUCCESSFULLY played events get status="fired" for deduplication.
        # Failed playback gets status="failed" and is eligible for retry.
        for ev in pending_events:
            prayer_store.add_event({
                "kind": "adhan",
                "prayer": ev.get("prayer"),
                "time": ev.get("time"),
                "message": ev.get("message"),
                "target_node": target_node,
                "media_id": media_id,
                "delivery": playback_result,
                "status": "fired" if played else "failed",
            })

        return {
            "status": "played" if played else "failed",
            "events": pending_events,
            "result": playback_result,
            "media_state": "verified" if media_id else self.ADHAN_MEDIA_REQUIRED,
        }

    def mark_adhan_fired(self, prayer: str) -> None:
        """Record that an adhan has been fired for this prayer occurrence.

        Used for deduplication across polling restarts.
        """
        prayer_store.add_event({
            "kind": "adhan",
            "prayer": prayer,
            "status": "fired",
        })


prayer_intelligence_service = PrayerIntelligenceService()

# --------------------------------------------------
# Automatic Adhan scheduler
#
# Runs check_adhan_due() every SCHEDULER_INTERVAL_SECONDS
# in a background daemon thread. Starts with application
# startup and stops cleanly with shutdown.
# --------------------------------------------------
import threading as _threading
from datetime import timezone as _timezone

SCHEDULER_INTERVAL_SECONDS = 30

_scheduler_lock = _threading.Lock()
_scheduler_thread: _threading.Thread | None = None
_scheduler_stop = _threading.Event()
_scheduler_state: dict[str, Any] = {
    "running": False,
    "interval_seconds": SCHEDULER_INTERVAL_SECONDS,
    "last_check": None,
    "last_result": None,
    "last_error": None,
}


def _scheduler_loop() -> None:
    """Background thread loop for automatic Adhan scheduling."""
    while not _scheduler_stop.is_set():
        try:
            result = prayer_intelligence_service.check_adhan_due()
            _scheduler_state["last_check"] = (
                datetime.now(_timezone.utc).isoformat()
            )
            _scheduler_state["last_result"] = result.get("status")
            _scheduler_state["last_error"] = None
        except Exception as exc:
            _scheduler_state["last_error"] = str(exc)
            _scheduler_state["last_check"] = (
                datetime.now(_timezone.utc).isoformat()
            )
        _scheduler_stop.wait(SCHEDULER_INTERVAL_SECONDS)


def start_adhan_scheduler(interval_seconds: float = SCHEDULER_INTERVAL_SECONDS) -> dict[str, Any]:
    """Start the automatic Adhan scheduler background thread."""
    global _scheduler_thread
    with _scheduler_lock:
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return {"status": "already_running"}
        _scheduler_stop.clear()
        _scheduler_state["running"] = True
        _scheduler_state["interval_seconds"] = int(interval_seconds)
        _scheduler_thread = _threading.Thread(
            target=_scheduler_loop,
            daemon=True,
            name="AdhanScheduler",
        )
        _scheduler_thread.start()
        return {"status": "started", "interval_seconds": int(interval_seconds)}


def stop_adhan_scheduler(timeout: float = 5.0) -> dict[str, Any]:
    """Stop the automatic Adhan scheduler background thread."""
    global _scheduler_thread
    with _scheduler_lock:
        _scheduler_stop.set()
        if _scheduler_thread is not None:
            _scheduler_thread.join(timeout=timeout)
        _scheduler_thread = None
        _scheduler_state["running"] = False
        return {"status": "stopped"}


def adhan_scheduler_status() -> dict[str, Any]:
    """Return current scheduler runtime truth."""
    return dict(_scheduler_state)
