"""
============================================================
Project : NoorBrain
Module  : Detection Manager
Version : 1.0.0
============================================================
"""

import threading
import time


class DetectionManager:

    def __init__(self):

        self._lock = threading.Lock()

        self._detections = []

        self._history = []

        self._frame_id = 0

        self._last_update = 0

        self._person_count = 0

        self._total_detections = 0

    # ----------------------------------------------------

    def update(self, detections):

        now = time.time()

        with self._lock:

            self._frame_id += 1

            self._last_update = now

            self._detections = list(detections)

            self._person_count = len(detections)

            self._total_detections += len(detections)

            self._history.append({

                "frame": self._frame_id,

                "timestamp": now,

                "count": len(detections),

                "detections": list(detections)

            })

            if len(self._history) > 500:

                self._history.pop(0)
    # ----------------------------------------------------

    def latest(self):

        with self._lock:

            return list(self._detections)

    # ----------------------------------------------------

    def history(self):

        with self._lock:

            return list(self._history)

    # ----------------------------------------------------

    def clear(self):

        with self._lock:

            self._detections.clear()

            self._history.clear()

            self._frame_id = 0

            self._person_count = 0

            self._total_detections = 0

            self._last_update = 0

    # ----------------------------------------------------

    def person_count(self):

        with self._lock:

            return self._person_count

    # ----------------------------------------------------

    def frame_count(self):

        with self._lock:

            return self._frame_id

    # ----------------------------------------------------

    def total_detections(self):

        with self._lock:

            return self._total_detections

    # ----------------------------------------------------

    def snapshot(self):

        with self._lock:

            return {

                "frame": self._frame_id,

                "persons": self._person_count,

                "latest": len(self._detections),

                "history": len(self._history),

                "total": self._total_detections,

                "last_update": self._last_update

            }


detection_manager = DetectionManager()
