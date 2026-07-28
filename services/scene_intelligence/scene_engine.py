"""Sprint 8.1: lightweight scene intelligence built on existing NoorBrain state."""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict, List

from services.event_engine import event_engine
from services.vision_engine import vision_engine


class SceneEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._last_occupied = False
        self._last_zones: Dict[str, int] = {}
        self._last_update = 0.0
        self._transitions = deque(maxlen=200)

    def _classify(self, person_count: int, zones: Dict[str, int]) -> str:
        if person_count <= 0:
            return "empty"
        if person_count == 1:
            return "single_person"
        if len(zones) <= 1:
            return "grouped"
        return "multi_zone"

    def analyze(self) -> Dict[str, Any]:
        now = time.time()
        detections: List[Dict[str, Any]] = vision_engine.get_detections()
        zones: Dict[str, int] = {}
        confidences: List[float] = []

        for item in detections:
            zone = str(item.get("zone") or "Unknown")
            zones[zone] = zones.get(zone, 0) + 1
            try:
                confidences.append(float(item.get("confidence", 0.0)))
            except (TypeError, ValueError):
                pass

        person_count = len(detections)
        occupied = person_count > 0
        transition = None

        with self._lock:
            if occupied != self._last_occupied:
                transition = "occupied" if occupied else "vacant"
            elif zones != self._last_zones and occupied:
                transition = "zone_changed"

            if transition:
                self._transitions.append({
                    "time": now,
                    "transition": transition,
                    "person_count": person_count,
                    "zones": dict(zones),
                })

            self._last_occupied = occupied
            self._last_zones = dict(zones)
            self._last_update = now

        primary_zone = max(zones, key=zones.get) if zones else None
        avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        return {
            "status": "ok",
            "timestamp": now,
            "occupied": occupied,
            "person_count": person_count,
            "scene_type": self._classify(person_count, zones),
            "primary_zone": primary_zone,
            "zones": zones,
            "average_confidence": avg_confidence,
            "transition": transition,
            "recognized_people": event_engine.snapshot().get("current_people", []),
        }

    def timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._transitions)[-max(1, min(limit, 200)):]

    def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "service": "scene_intelligence",
            "version": "8.1.0",
            "vision_running": bool(vision_engine.snapshot().get("running")),
        }


scene_engine = SceneEngine()
