from collections import deque
from datetime import datetime
import threading
import time


class ActivityEngine:
    def __init__(
        self,
        disappearance_timeout=3.5,
        stay_interval=60.0,
        maximum_events=500
    ):
        self.disappearance_timeout = float(
            disappearance_timeout
        )
        self.stay_interval = float(
            stay_interval
        )

        self._lock = threading.RLock()
        self._people = {}
        self._events = deque(
            maxlen=maximum_events
        )
        self._pending_events = deque()
        self._next_event_id = 1

    @staticmethod
    def _clean_zone(zone):
        if zone is None:
            return None

        zone = str(zone).strip()

        if not zone:
            return None

        if zone.lower() in {
            "none",
            "unknown",
            "unassigned"
        }:
            return None

        return zone

    def _add_event(
        self,
        event_type,
        person_id,
        duration=None,
        zone=None,
        previous_zone=None
    ):
        now = time.time()

        zone = self._clean_zone(zone)
        previous_zone = self._clean_zone(
            previous_zone
        )

        event = {
            "event_id": self._next_event_id,
            "type": event_type,
            "person_id": int(person_id),
            "zone": zone,
            "previous_zone": previous_zone,
            "timestamp": now,
            "time_text": (
                datetime.fromtimestamp(now)
                .strftime("%Y-%m-%d %H:%M:%S")
            ),
        }

        if duration is not None:
            event["duration"] = round(
                float(duration),
                1
            )

        if event_type == "appeared":
            event["message"] = (
                f"Person {person_id} appeared"
                + (
                    f" in {zone}"
                    if zone else ""
                )
            )

        elif event_type == "entered_zone":
            event["message"] = (
                f"Person {person_id} entered "
                f"{zone}"
            )

        elif event_type == "moved_zone":
            event["message"] = (
                f"Person {person_id} moved "
                f"from {previous_zone} to {zone}"
            )

        elif event_type == "left_zone":
            event["message"] = (
                f"Person {person_id} left "
                f"{previous_zone or zone}"
            )

        elif event_type == "stayed":
            event["message"] = (
                f"Person {person_id} stayed"
                + (
                    f" in {zone}"
                    if zone else ""
                )
                + (
                    f" for {int(event.get('duration', 0))} "
                    "seconds"
                )
            )

        else:
            event["message"] = (
                f"Person {person_id} disappeared"
                + (
                    f" from {previous_zone or zone}"
                    if (previous_zone or zone)
                    else ""
                )
            )

        self._events.appendleft(event)
        self._pending_events.append(
            dict(event)
        )

        self._next_event_id += 1

    def update(self, detections):
        now = time.time()
        visible = set()

        with self._lock:

            for detection in detections:

                person_id = detection.get(
                    "person_id",
                    detection.get("id")
                )

                try:
                    person_id = int(person_id)
                except (TypeError, ValueError):
                    continue

                zone = self._clean_zone(
                    detection.get("zone")
                )

                visible.add(person_id)

                person = self._people.get(
                    person_id
                )

                # -------------------------
                # NEW PERSON
                # -------------------------

                if person is None:

                    self._people[person_id] = {
                        "person_id": person_id,
                        "first_seen": now,
                        "last_seen": now,
                        "last_stay_event": now,
                        "visible": True,
                        "zone": zone,
                        "previous_zone": None,
                    }

                    self._add_event(
                        "appeared",
                        person_id,
                        zone=zone
                    )

                    if zone:
                        self._add_event(
                            "entered_zone",
                            person_id,
                            zone=zone
                        )

                    continue

                # -------------------------
                # EXISTING PERSON
                # -------------------------

                old_zone = self._clean_zone(
                    person.get("zone")
                )

                person["last_seen"] = now
                person["visible"] = True

                # Zone transition.
                if zone != old_zone:

                    if old_zone and zone:

                        self._add_event(
                            "moved_zone",
                            person_id,
                            zone=zone,
                            previous_zone=old_zone
                        )

                    elif zone and not old_zone:

                        self._add_event(
                            "entered_zone",
                            person_id,
                            zone=zone
                        )

                    elif old_zone and not zone:

                        self._add_event(
                            "left_zone",
                            person_id,
                            zone=None,
                            previous_zone=old_zone
                        )

                    person["previous_zone"] = (
                        old_zone
                    )

                    person["zone"] = zone

                if (
                    now
                    - person["last_stay_event"]
                    >= self.stay_interval
                ):

                    self._add_event(
                        "stayed",
                        person_id,
                        now - person["first_seen"],
                        zone=person.get("zone"),
                        previous_zone=(
                            person.get(
                                "previous_zone"
                            )
                        )
                    )

                    person[
                        "last_stay_event"
                    ] = now

            # -------------------------
            # DISAPPEARED PEOPLE
            # -------------------------

            expired = []

            for person_id, person in (
                self._people.items()
            ):

                if person_id in visible:
                    continue

                if (
                    now - person["last_seen"]
                    < self.disappearance_timeout
                ):
                    person["visible"] = False
                    continue

                last_zone = self._clean_zone(
                    person.get("zone")
                )

                if last_zone:
                    self._add_event(
                        "left_zone",
                        person_id,
                        duration=(
                            now
                            - person["first_seen"]
                        ),
                        previous_zone=last_zone
                    )

                self._add_event(
                    "disappeared",
                    person_id,
                    now - person["first_seen"],
                    zone=last_zone,
                    previous_zone=last_zone
                )

                expired.append(
                    person_id
                )

            for person_id in expired:
                del self._people[person_id]

    def drain_events(self):
        with self._lock:
            events = list(
                self._pending_events
            )

            self._pending_events.clear()

            return events

    def events(self, limit=100):
        with self._lock:
            return list(
                self._events
            )[
                :max(
                    1,
                    min(
                        int(limit),
                        500
                    )
                )
            ]

    def active_people(self):
        now = time.time()

        with self._lock:

            return [
                {
                    "person_id":
                        p["person_id"],

                    "zone":
                        p.get("zone"),

                    "previous_zone":
                        p.get(
                            "previous_zone"
                        ),

                    "visible":
                        p["visible"],

                    "first_seen":
                        p["first_seen"],

                    "last_seen":
                        p["last_seen"],

                    "seen_for":
                        round(
                            now
                            - p["first_seen"],
                            1
                        ),

                    "presence_duration":
                        round(
                            now
                            - p["first_seen"],
                            1
                        ),
                }

                for p in
                self._people.values()
            ]

    def snapshot(self, limit=100):
        return {
            "status": "running",
            "mode": "single_camera",

            "zones_enabled": True,

            "supported_events": [
                "appeared",
                "entered_zone",
                "moved_zone",
                "left_zone",
                "stayed",
                "disappeared",
            ],

            "active_count":
                len(self._people),

            "event_count":
                len(self._events),

            "disappearance_timeout":
                self.disappearance_timeout,

            "stay_interval":
                self.stay_interval,

            "active_people":
                self.active_people(),

            "events":
                self.events(limit),
        }

    def clear(self):
        with self._lock:
            self._events.clear()
            self._pending_events.clear()
            self._people.clear()
            self._next_event_id = 1

        return {
            "status": "cleared",
            "mode": "single_camera"
        }


activity_engine = ActivityEngine()
