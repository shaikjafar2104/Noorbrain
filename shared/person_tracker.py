"""
NoorBrain Person Tracker
Stable IDs for YOLO person detections.
"""

import math
import threading
import time


class PersonTracker:
    def __init__(
        self,
        maximum_distance=180,
        missing_timeout=2.5,
        minimum_hits=2
    ):
        self.maximum_distance = maximum_distance
        self.missing_timeout = missing_timeout
        self.minimum_hits = minimum_hits

        self._lock = threading.Lock()
        self._tracks = {}
        self._next_id = 1

    @staticmethod
    def _center(box):
        x1, y1, x2, y2 = box
        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0
        )

    @staticmethod
    def _distance(first, second):
        return math.hypot(
            first[0] - second[0],
            first[1] - second[1]
        )

    def _create_track(self, detection, now):
        person_id = self._next_id
        self._next_id += 1

        center = self._center(detection["box"])

        self._tracks[person_id] = {
            "id": person_id,
            "center": center,
            "box": list(detection["box"]),
            "zone": detection.get("zone", "Unknown"),
            "previous_zone": None,
            "confidence": detection.get("confidence", 0),
            "first_seen": now,
            "last_seen": now,
            "hits": 1,
            "visible": True
        }

        return person_id

    def update(self, detections):
        now = time.time()

        with self._lock:
            for track in self._tracks.values():
                track["visible"] = False

            available_tracks = set(self._tracks.keys())
            results = []

            ordered_detections = sorted(
                detections,
                key=lambda item: item.get("confidence", 0),
                reverse=True
            )

            for detection in ordered_detections:
                box = detection.get("box")

                if not box or len(box) != 4:
                    continue

                center = self._center(box)
                best_id = None
                best_distance = self.maximum_distance

                for person_id in available_tracks:
                    track = self._tracks[person_id]

                    if now - track["last_seen"] > self.missing_timeout:
                        continue

                    distance = self._distance(
                        center,
                        track["center"]
                    )

                    if distance < best_distance:
                        best_distance = distance
                        best_id = person_id

                if best_id is None:
                    best_id = self._create_track(
                        detection,
                        now
                    )
                else:
                    track = self._tracks[best_id]
                    old_zone = track["zone"]
                    new_zone = detection.get(
                        "zone",
                        "Unknown"
                    )

                    track.update({
                        "center": center,
                        "box": list(box),
                        "previous_zone": (
                            old_zone
                            if old_zone != new_zone
                            else track["previous_zone"]
                        ),
                        "zone": new_zone,
                        "confidence": detection.get(
                            "confidence",
                            0
                        ),
                        "last_seen": now,
                        "hits": track["hits"] + 1,
                        "visible": True
                    })

                    available_tracks.discard(best_id)

                track = self._tracks[best_id]

                enriched = dict(detection)
                enriched.update({
                    "id": best_id,
                    "person_id": best_id,
                    "first_seen": track["first_seen"],
                    "last_seen": track["last_seen"],
                    "seen_for": round(
                        now - track["first_seen"],
                        1
                    ),
                    "hits": track["hits"],
                    "status": (
                        "active"
                        if track["hits"] >= self.minimum_hits
                        else "confirming"
                    ),
                    "previous_zone": track["previous_zone"]
                })

                results.append(enriched)

            expired = [
                person_id
                for person_id, track in self._tracks.items()
                if now - track["last_seen"] > self.missing_timeout
            ]

            for person_id in expired:
                del self._tracks[person_id]

            return results

    def active(self):
        now = time.time()

        with self._lock:
            return [
                {
                    "id": track["id"],
                    "zone": track["zone"],
                    "previous_zone": track["previous_zone"],
                    "box": list(track["box"]),
                    "confidence": track["confidence"],
                    "first_seen": track["first_seen"],
                    "last_seen": track["last_seen"],
                    "seen_for": round(
                        now - track["first_seen"],
                        1
                    ),
                    "hits": track["hits"],
                    "visible": track["visible"],
                    "status": (
                        "active"
                        if track["visible"]
                        else "temporarily_missing"
                    )
                }
                for track in self._tracks.values()
            ]

    def snapshot(self):
        tracks = self.active()

        return {
            "active_tracks": len(tracks),
            "next_id": self._next_id,
            "maximum_distance": self.maximum_distance,
            "missing_timeout": self.missing_timeout,
            "tracks": tracks
        }

    def reset(self):
        with self._lock:
            self._tracks.clear()
            self._next_id = 1


person_tracker = PersonTracker()
