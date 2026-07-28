import threading
from datetime import datetime

from services.event_engine.event_engine import event_engine
from services.person_ai.face_models import face_models
from services.person_ai.face_recognition import face_recognition
from services.person_ai.face_tracking import face_tracking
from services.person_ai.person_registry import registry


class IdentityEngine:
    def __init__(self):
        self.lock = threading.RLock()
        self.version = "Sprint 5.5"
        self.last_processed_at = None
        self.last_results = []
        self.frames_processed = 0

    def process_frame(self, frame):
        results = face_recognition.recognize(frame)
        tracked_people = face_tracking.update(results)

        event_engine.update_people(tracked_people)

        now = datetime.now().astimezone().isoformat()

        with self.lock:
            self.last_processed_at = now
            self.last_results = results
            self.frames_processed += 1

        return {
            "status": "ready",
            "processed_at": now,
            "faces_detected": len(results),
            "recognized_count": sum(
                1
                for result in results
                if result.get("status")
                == "recognized"
            ),
            "unknown_count": sum(
                1
                for result in results
                if result.get("status")
                == "unknown"
            ),
            "results": results,
            "current_people": tracked_people,
        }

    def status(self):
        persons = registry.all()

        registered_faces = sum(
            1
            for person in persons
            if person.get(
                "face_registered",
                False,
            )
        )

        current_people = (
            face_tracking.current_people()
        )

        with self.lock:
            return {
                "status": "ready",
                "version": self.version,
                "models": face_models.status(),
                "registered_persons": len(persons),
                "face_registered_persons": (
                    registered_faces
                ),
                "frames_processed": (
                    self.frames_processed
                ),
                "last_processed_at": (
                    self.last_processed_at
                ),
                "current_people_count": len(
                    current_people
                ),
            }

    def current(self):
        current_people = (
            face_tracking.current_people()
        )

        with self.lock:
            return {
                "status": "ready",
                "last_processed_at": (
                    self.last_processed_at
                ),
                "faces": list(
                    self.last_results
                ),
                "current_people": (
                    current_people
                ),
                "presence": (
                    event_engine.snapshot()
                ),
            }


identity_engine = IdentityEngine()
