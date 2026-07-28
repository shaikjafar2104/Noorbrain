from collections import deque
from datetime import datetime
import threading
import time


class ActivityEngine:
    def __init__(self, disappearance_timeout=3.5, stay_interval=60.0, maximum_events=500):
        self.disappearance_timeout = float(disappearance_timeout)
        self.stay_interval = float(stay_interval)
        self._lock = threading.RLock()
        self._people = {}
        self._events = deque(maxlen=maximum_events)
        self._pending_events = deque()
        self._next_event_id = 1

    def _add_event(self, event_type, person_id, duration=None):
        now = time.time()
        event = {
            "event_id": self._next_event_id,
            "type": event_type,
            "person_id": int(person_id),
            "zone": None,
            "previous_zone": None,
            "timestamp": now,
            "time_text": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S"),
        }
        if duration is not None:
            event["duration"] = round(float(duration), 1)
        if event_type == "appeared":
            event["message"] = f"Person {person_id} appeared"
        elif event_type == "stayed":
            event["message"] = f"Person {person_id} stayed for {int(event.get('duration', 0))} seconds"
        else:
            event["message"] = f"Person {person_id} disappeared"
        self._events.appendleft(event)
        self._pending_events.append(dict(event))
        self._next_event_id += 1

    def update(self, detections):
        now = time.time()
        visible = set()
        with self._lock:
            for detection in detections:
                person_id = detection.get("person_id", detection.get("id"))
                try:
                    person_id = int(person_id)
                except (TypeError, ValueError):
                    continue
                visible.add(person_id)
                person = self._people.get(person_id)
                if person is None:
                    self._people[person_id] = {
                        "person_id": person_id,
                        "first_seen": now,
                        "last_seen": now,
                        "last_stay_event": now,
                        "visible": True,
                    }
                    self._add_event("appeared", person_id)
                    continue
                person["last_seen"] = now
                person["visible"] = True
                if now - person["last_stay_event"] >= self.stay_interval:
                    self._add_event("stayed", person_id, now - person["first_seen"])
                    person["last_stay_event"] = now

            expired = []
            for person_id, person in self._people.items():
                if person_id in visible:
                    continue
                if now - person["last_seen"] < self.disappearance_timeout:
                    person["visible"] = False
                    continue
                self._add_event("disappeared", person_id, now - person["first_seen"])
                expired.append(person_id)
            for person_id in expired:
                del self._people[person_id]

    def drain_events(self):
        with self._lock:
            events = list(self._pending_events)
            self._pending_events.clear()
            return events

    def events(self, limit=100):
        with self._lock:
            return list(self._events)[:max(1, min(int(limit), 500))]

    def active_people(self):
        now = time.time()
        with self._lock:
            return [{
                "person_id": p["person_id"],
                "zone": None,
                "visible": p["visible"],
                "first_seen": p["first_seen"],
                "last_seen": p["last_seen"],
                "seen_for": round(now - p["first_seen"], 1),
                "presence_duration": round(now - p["first_seen"], 1),
            } for p in self._people.values()]

    def snapshot(self, limit=100):
        return {
            "status": "running",
            "mode": "single_camera",
            "zones_enabled": False,
            "supported_events": ["appeared", "stayed", "disappeared"],
            "active_count": len(self._people),
            "event_count": len(self._events),
            "disappearance_timeout": self.disappearance_timeout,
            "stay_interval": self.stay_interval,
            "active_people": self.active_people(),
            "events": self.events(limit),
        }

    def clear(self):
        with self._lock:
            self._events.clear()
            self._pending_events.clear()
            self._people.clear()
            self._next_event_id = 1
        return {"status": "cleared", "mode": "single_camera"}


activity_engine = ActivityEngine()
