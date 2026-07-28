"""
============================================================
Project : NoorBrain
Module  : Event Engine
Version : 1.1.0
Purpose : Zone and recognized-person presence events
============================================================
"""

import threading
import time

from shared.database import database
from shared.logger import logger


class EventEngine:
    def __init__(self):
        self.lock = threading.RLock()

        self.events = []
        self.max_events = 1000

        self.current_zone = None
        self.last_seen = None

        self.current_people = {}
        self.person_timeout_seconds = 12

    # ----------------------------------------------------
    @staticmethod
    def _clean_zone(zone):
        if zone is None:
            return "Unknown"

        zone = str(zone).strip()

        if not zone or zone.lower() == "none":
            return "Unknown"

        return zone

    # ----------------------------------------------------
    def _append_event(self, event):
        self.events.append(event)

        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    # ----------------------------------------------------
    def update(self, detections):
        now = time.time()

        with self.lock:
            if not detections:
                if self.current_zone is not None:
                    zone = self._clean_zone(
                        self.current_zone
                    )

                    event = {
                        "time": now,
                        "event": "left",
                        "zone": zone,
                    }

                    self._append_event(event)

                    database.add_event(
                        now,
                        "left",
                        zone=zone,
                    )

                    logger.info(
                        "EVENT : Left %s",
                        zone,
                    )

                    self.current_zone = None

                return

            zone = self._clean_zone(
                detections[0].get("zone")
            )

            if self.current_zone is None:
                self.current_zone = zone

                event = {
                    "time": now,
                    "event": "entered",
                    "zone": zone,
                }

                self._append_event(event)

                database.add_event(
                    now,
                    "entered",
                    zone=zone,
                )

                logger.info(
                    "EVENT : Entered %s",
                    zone,
                )

            elif zone != self.current_zone:
                old_zone = self._clean_zone(
                    self.current_zone
                )

                self.current_zone = zone

                event = {
                    "time": now,
                    "event": "moved",
                    "from": old_zone,
                    "to": zone,
                }

                self._append_event(event)

                database.add_event(
                    now,
                    "moved",
                    source=old_zone,
                    destination=zone,
                )

                logger.info(
                    "EVENT : %s -> %s",
                    old_zone,
                    zone,
                )

            self.last_seen = now

    # ----------------------------------------------------
    def update_people(self, tracked_people):
        now = time.time()

        with self.lock:
            seen_ids = set()

            for record in tracked_people or []:
                person = record.get("person") or {}
                person_id = record.get(
                    "person_id",
                    person.get("person_id"),
                )

                if not person_id:
                    continue

                seen_ids.add(person_id)

                name = (
                    person.get("name")
                    or "Unknown Person"
                )

                confidence = float(
                    record.get(
                        "confidence_percent",
                        0.0,
                    )
                    or 0.0
                )

                zone = self._clean_zone(
                    record.get(
                        "zone",
                        self.current_zone,
                    )
                )

                existing = self.current_people.get(
                    person_id
                )

                if existing is None:
                    first_seen = now

                    event = {
                        "time": now,
                        "event": "person_entered",
                        "person_id": person_id,
                        "person_name": name,
                        "zone": zone,
                        "confidence_percent": round(
                            confidence,
                            2,
                        ),
                    }

                    self._append_event(event)

                    try:
                        database.add_event(
                            now,
                            "person_entered",
                            zone=zone,
                        )
                    except Exception:
                        logger.exception(
                            "Person entered database write failed"
                        )

                    logger.info(
                        "EVENT : %s entered %s "
                        "(%.2f%%)",
                        name,
                        zone,
                        confidence,
                    )
                else:
                    first_seen = existing[
                        "first_seen"
                    ]

                self.current_people[person_id] = {
                    "person_id": person_id,
                    "person_name": name,
                    "zone": zone,
                    "confidence_percent": round(
                        confidence,
                        2,
                    ),
                    "first_seen": first_seen,
                    "last_seen": now,
                    "presence_seconds": round(
                        now - first_seen,
                        1,
                    ),
                }

            expired = []

            for person_id, record in (
                self.current_people.items()
            ):
                if person_id in seen_ids:
                    continue

                absence = now - record["last_seen"]

                if absence >= self.person_timeout_seconds:
                    expired.append(person_id)

            for person_id in expired:
                record = self.current_people.pop(
                    person_id
                )

                duration = round(
                    record["last_seen"]
                    - record["first_seen"],
                    1,
                )

                event = {
                    "time": now,
                    "event": "person_left",
                    "person_id": person_id,
                    "person_name": record[
                        "person_name"
                    ],
                    "zone": record["zone"],
                    "presence_seconds": duration,
                }

                self._append_event(event)

                try:
                    database.add_event(
                        now,
                        "person_left",
                        zone=record["zone"],
                    )
                except Exception:
                    logger.exception(
                        "Person left database write failed"
                    )

                logger.info(
                    "EVENT : %s left %s "
                    "(present %.1f seconds)",
                    record["person_name"],
                    record["zone"],
                    duration,
                )

    # ----------------------------------------------------
    def recent(self, count=20):
        with self.lock:
            return list(
                self.events[-max(1, count):]
            )

    # ----------------------------------------------------
    def history(self):
        with self.lock:
            return list(self.events)

    # ----------------------------------------------------
    def current(self):
        with self.lock:
            return self.current_zone

    # ----------------------------------------------------
    def snapshot(self):
        with self.lock:
            return {
                "current_zone": self.current_zone,
                "events": len(self.events),
                "last_seen": self.last_seen,
                "current_people_count": len(
                    self.current_people
                ),
                "current_people": [
                    dict(record)
                    for record in (
                        self.current_people.values()
                    )
                ],
            }


event_engine = EventEngine()
