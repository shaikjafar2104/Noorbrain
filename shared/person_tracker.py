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
            "last_center": center,
            "last_motion_time": now,
            "displacement_px": 0.0,
            "velocity_px_s": 0.0,
            "motion_state": "stationary",
            "motion_state_started": now,
            "moving_streak": 0,
            "stationary_streak": 0,
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

                    dt = now - track["last_seen"]
                    prev_center = track["center"]
                    displacement = self._distance(center, prev_center)
                    velocity = displacement / dt if dt > 0 else 0.0

                    # Motion state with debounce
                    motion_state = track.get("motion_state", "stationary")
                    moving_streak = track.get("moving_streak", 0) + 1 if displacement > 3.0 else 0
                    stationary_streak = track.get("stationary_streak", 0) + 1 if displacement <= 3.0 else 0

                    # Debounce: require 2 consecutive moving frames to switch
                    if moving_streak >= 2 and motion_state != "moving":
                        motion_state = "moving"
                        motion_state_started = now
                    elif stationary_streak >= 2 and motion_state != "stationary":
                        motion_state = "stationary"
                        motion_state_started = now
                    else:
                        motion_state_started = track.get("motion_state_started", now)

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
                        "last_center": prev_center,
                        "last_motion_time": now,
                        "displacement_px": round(displacement, 2),
                        "velocity_px_s": round(velocity, 2),
                        "motion_state": motion_state,
                        "motion_state_started": motion_state_started,
                        "moving_streak": moving_streak,
                        "stationary_streak": stationary_streak,
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
                    "previous_zone": track["previous_zone"],
                    "center": track["center"],
                    "displacement_px": track["displacement_px"],
                    "velocity_px_s": track["velocity_px_s"],
                    "motion_state": track["motion_state"],
                    "motion_duration": round(
                        now - track["motion_state_started"],
                        1
                    ),
                    "direction": round(
                        math.degrees(
                            math.atan2(
                                track.get("center", (0, 0))[0] - track.get("last_center", track.get("center", (0, 0)))[0],
                                track.get("center", (0, 0))[1] - track.get("last_center", track.get("center", (0, 0)))[1]
                            )
                        ),
                        1
                    ) if displacement > 0 else 0.0,
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
                    ),
                    "center": track["center"],
                    "displacement_px": track["displacement_px"],
                    "velocity_px_s": track["velocity_px_s"],
                    "motion_state": track["motion_state"],
                    "motion_duration": round(
                        now - track["motion_state_started"],
                        1
                    ),
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
