from __future__ import annotations

from typing import Any

from .geometry import point_in_polygon
from .store import zone_store


class VisionZoneService:
    def zones_for_point(
        self,
        *,
        camera_id: str,
        x: float,
        y: float,
    ) -> list[dict[str, Any]]:
        matches = []

        for zone in zone_store.list_zones():
            if not zone.get("enabled", True):
                continue

            if zone.get("camera_id", "primary") != camera_id:
                continue

            if point_in_polygon(x, y, zone.get("points", [])):
                matches.append(zone)

        return matches

    def record_motion(
        self,
        *,
        camera_id: str,
        x: float,
        y: float,
        confidence: float,
        source: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        matches = self.zones_for_point(
            camera_id=camera_id,
            x=x,
            y=y,
        )

        events = []

        if not matches:
            events.append(
                zone_store.add_motion_event({
                    "camera_id": camera_id,
                    "zone_id": None,
                    "zone_name": None,
                    "x": x,
                    "y": y,
                    "confidence": confidence,
                    "source": source,
                    "metadata": metadata,
                })
            )
        else:
            for zone in matches:
                events.append(
                    zone_store.add_motion_event({
                        "camera_id": camera_id,
                        "zone_id": zone["id"],
                        "zone_name": zone["name"],
                        "x": x,
                        "y": y,
                        "confidence": confidence,
                        "source": source,
                        "metadata": metadata,
                    })
                )

        self._mirror_to_vision_events(events)

        return {
            "status": "recorded",
            "matched_zone_count": len(matches),
            "matched_zones": [
                {"id": zone["id"], "name": zone["name"]}
                for zone in matches
            ],
            "events": events,
        }

    @staticmethod
    def _mirror_to_vision_events(
        events: list[dict[str, Any]],
    ) -> None:
        try:
            from services.vision_intelligence.store import vision_event_store
        except Exception:
            return

        for event in events:
            vision_event_store.add({
                "event_type": "motion_detected",
                "source": event.get("source", "vision_zones"),
                "zone": event.get("zone_name"),
                "person_id": None,
                "confidence": event.get("confidence"),
                "message": (
                    f"Motion detected"
                    + (
                        f" in {event['zone_name']}"
                        if event.get("zone_name")
                        else ""
                    )
                    + "."
                ),
                "snapshot_path": None,
                "metadata": {
                    "zone_id": event.get("zone_id"),
                    "x": event.get("x"),
                    "y": event.get("y"),
                    **dict(event.get("metadata") or {}),
                },
            })


vision_zone_service = VisionZoneService()
