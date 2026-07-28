from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .store import presence_store, utc_now

def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

class PersonPresenceService:
    def update(self, item: dict[str, Any]) -> dict[str, Any]:
        data = presence_store.read()
        tracks = data["active_tracks"]
        track_id = str(item["track_id"])
        now = utc_now()
        current = tracks.get(track_id)

        if current is None:
            current = {
                "track_id": track_id,
                "first_seen": now,
                "last_seen": now,
                "camera_id": item.get("camera_id", "primary"),
                "zone": item.get("zone"),
                "previous_zone": None,
                "confidence": item.get("confidence", 1.0),
                "person_id": item.get("person_id"),
                "status": "active",
                "transition_count": 0,
                "metadata": dict(item.get("metadata") or {}),
            }
            event_type = "person_entered"
            message = f"Track {track_id} entered."
        else:
            old_zone = current.get("zone")
            new_zone = item.get("zone")
            current.update({
                "last_seen": now,
                "camera_id": item.get("camera_id", current.get("camera_id")),
                "zone": new_zone,
                "confidence": item.get("confidence", current.get("confidence")),
                "person_id": item.get("person_id") or current.get("person_id"),
                "status": "active",
                "metadata": {**dict(current.get("metadata") or {}), **dict(item.get("metadata") or {})},
            })
            if old_zone != new_zone:
                current["previous_zone"] = old_zone
                current["transition_count"] = int(current.get("transition_count", 0)) + 1
                event_type = "zone_transition"
                message = f"Track {track_id} moved from {old_zone or 'unassigned'} to {new_zone or 'unassigned'}."
            else:
                event_type = "track_updated"
                message = f"Track {track_id} updated."

        tracks[track_id] = current
        data["active_tracks"] = tracks
        presence_store.write(data)

        event = presence_store.append_event({
            "event_type": event_type,
            "track_id": track_id,
            "zone": current.get("zone"),
            "previous_zone": current.get("previous_zone"),
            "person_id": current.get("person_id"),
            "confidence": current.get("confidence"),
            "message": message,
        })
        self._mirror(event)
        return {"status": "ok", "track": current, "event": event}

    def cleanup(self, stale_after_seconds: float) -> dict[str, Any]:
        data = presence_store.read()
        tracks = data["active_tracks"]
        now = datetime.now(timezone.utc)
        removed = []

        for track_id, track in list(tracks.items()):
            if (now - parse_time(track["last_seen"])).total_seconds() >= stale_after_seconds:
                removed.append(track)
                del tracks[track_id]

        data["active_tracks"] = tracks
        presence_store.write(data)

        events = []
        for track in removed:
            dwell = max(0.0, (parse_time(track["last_seen"]) - parse_time(track["first_seen"])).total_seconds())
            event = presence_store.append_event({
                "event_type": "person_exited",
                "track_id": track["track_id"],
                "zone": track.get("zone"),
                "previous_zone": track.get("previous_zone"),
                "person_id": track.get("person_id"),
                "confidence": track.get("confidence"),
                "message": f"Track {track['track_id']} exited.",
                "metadata": {"dwell_seconds": round(dwell, 2)},
            })
            events.append(event)
            self._mirror(event)

        return {"status": "ok", "removed_count": len(removed), "active_count": len(tracks), "events": events}

    def summary(self) -> dict[str, Any]:
        data = presence_store.read()
        tracks = list(data["active_tracks"].values())
        by_zone: dict[str, int] = {}
        for track in tracks:
            zone = str(track.get("zone") or "unassigned")
            by_zone[zone] = by_zone.get(zone, 0) + 1
        return {"status": "ok", "active_count": len(tracks), "by_zone": by_zone, "tracks": tracks}

    @staticmethod
    def _mirror(event: dict[str, Any]) -> None:
        try:
            from services.vision_intelligence.store import vision_event_store
            vision_event_store.add({
                "event_type": event.get("event_type"),
                "source": "person_presence",
                "zone": event.get("zone"),
                "person_id": event.get("person_id"),
                "confidence": event.get("confidence"),
                "message": event.get("message"),
                "snapshot_path": None,
                "metadata": {"track_id": event.get("track_id"), "previous_zone": event.get("previous_zone")},
            })
        except Exception:
            pass

person_presence_service = PersonPresenceService()
