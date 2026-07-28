import threading
from datetime import datetime, timedelta


class FaceTracking:
    def __init__(self):
        self.lock = threading.RLock()
        self.current = {}
        self.timeout_seconds = 10

    def update(self, recognition_results):
        now = datetime.now().astimezone()

        with self.lock:
            for result in recognition_results:
                if result.get("status") != "recognized":
                    continue

                person = result.get("person")

                if not person:
                    continue

                person_id = person.get("person_id")

                if not person_id:
                    continue

                existing = self.current.get(person_id)

                if existing is None:
                    first_seen = now
                    event = "entered"
                else:
                    first_seen = datetime.fromisoformat(
                        existing["first_seen"]
                    )
                    event = "present"

                confidence = result.get(
                    "confidence_percent",
                    result.get("confidence", 0.0),
                )

                duration = max(
                    0.0,
                    (now - first_seen).total_seconds(),
                )

                self.current[person_id] = {
                    "person_id": person_id,
                    "person": person,
                    "confidence_percent": round(
                        float(confidence or 0.0),
                        2,
                    ),
                    "first_seen": first_seen.isoformat(),
                    "last_seen": now.isoformat(),
                    "presence_seconds": round(duration, 1),
                    "event": event,
                }

            self._remove_expired(now)

            return self.current_people()

    def _remove_expired(self, now):
        expired = []

        for person_id, record in self.current.items():
            last_seen = datetime.fromisoformat(
                record["last_seen"]
            )

            if now - last_seen > timedelta(
                seconds=self.timeout_seconds
            ):
                expired.append(person_id)

        for person_id in expired:
            self.current.pop(person_id, None)

    def current_people(self):
        with self.lock:
            return [
                dict(record)
                for record in self.current.values()
            ]

    def clear(self):
        with self.lock:
            self.current.clear()


face_tracking = FaceTracking()
