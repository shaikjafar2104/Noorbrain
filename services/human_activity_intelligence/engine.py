"""
Human Activity Intelligence — temporal activity engine.

Consumes existing person-track/zone/object data and emits richer
activity observations into the existing event/rule pipeline.

PHONE USE: requires observed_objects containing a phone label associated
with the tracked person. Without reliable object association, the engine
falls back to LIMITED_CAPABILITY and emits nothing.

TV CONTEXT: probabilistic only. Requires configured TV-zone evidence
(zone in TV_CONTEXT_ZONES) PLUS stationary/sitting posture during the
evening window. Never treated as fact.

POSE: unavailable — this engine uses lightweight box/motion heuristics only.
No pose model is assumed.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .store import ActivityStore, SessionState

PHONE_LABELS = frozenset({
    "cell phone", "cell_phone", "phone", "mobile phone",
    "mobile_phone", "smartphone", "handphone",
})

# TV context zones — configurable, used for probabilistic TV context detection.
# Test engine can override this attribute to configure test-specific zones.
TV_CONTEXT_ZONES = frozenset({
    "Living Room", "Family Room", "Lounge", "TV Room",
})

TV_EVENING_START = 17  # 17:00 local-equivalent
TV_EVENING_END = 23    # 23:00

POSE_UNAVAILABLE = True
GRACEFUL_FALLBACK = True

# Tuning thresholds — conservative defaults
STANDING_HEIGHT_RATIO_MIN = 1.4
SITTING_HEIGHT_RATIO_MAX = 1.0
MOTION_MOVING_MIN = 8.0
MOTION_STATIONARY_MAX = 3.0
LONG_SITTING_THRESHOLD_SECONDS = 1800   # 30 min
LONG_INACTIVITY_THRESHOLD_SECONDS = 1800     # 30 min
INACTIVITY_THRESHOLD_SECONDS = LONG_INACTIVITY_THRESHOLD_SECONDS  # backward compat alias
LONG_STATIONARY_THRESHOLD_SECONDS = 900   # 15 min
SESSION_STALE_SECONDS = 600             # 10 min without observation
MOVEMENT_DEBOUNCE_FRAMES = 3  # Require 3 consecutive frames to switch motion state
CONFIDENCE_RAMP_PER_OBSERVATION = 0.08
CONFIDENCE_INITIAL_MAX = 0.75
CONFIDENCE_FLOOR = 0.45
CONFIDENCE_HIGH = 0.85

PHONE_USE_CAPABILITY = "LIMITED_CAPABILITY"
TV_CONTEXT_CAPABILITY = "PROBABILISTIC_ONLY"

# Phone-use dwell threshold: requires observed_objects evidence.
PHONE_USE_DWELL = 60  # seconds of sitting + phone object evidence


def _slug(*parts: str) -> str:
    raw = ":".join(p.strip() for p in parts if p.strip())
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch_to_hour(epoch: float) -> int:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).hour


class HumanActivityIntelligence:
    """Lightweight temporal activity classifier.

    State machine per (person_id, zone) pair:
      - start session when activity type first detected
      - update session as signals accumulate
      - end session when activity resolves / person leaves / timeout
      - emit events into activity_store (which the reminder_rules / islamic
        pipeline already reads via reminder_rules.handle_event() path)

    Confidence is conservative: posture from box height ratio, motion from
    track deltas. No pose model is assumed.
    """

    def __init__(self, store: ActivityStore | None = None) -> None:
        self._store = store or ActivityStore()
        self._sessions: dict[str, SessionState] = {}
        self._previous_zone: dict[str, str] = {}
        self._previous_motion_state: dict[str, str] = {}
        self._motion_frame_count: dict[str, int] = {}
        self._previous_posture: dict[str, str] = {}
        self._lock = threading.RLock()
        self._drain_stop = threading.Event()
        self._snapshot_stop = threading.Event()
        self._pattern_stop = threading.Event()
        self._drain_thread: threading.Thread | None = None
        self._snapshot_thread: threading.Thread | None = None
        self._pattern_thread: threading.Thread | None = None
        self._started_at = time.time()
        # Allow tests to override TV context zones
        self.tv_context_zones = TV_CONTEXT_ZONES

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def observe(
        self,
        *,
        person_id: str,
        track_id: str | None = None,
        zone: str = "",
        room: str | None = None,
        box: list[float] | None = None,
        motion_delta: float = 0.0,
        frame_epoch: float | None = None,
        observed_objects: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Process one person observation and return any emitted events."""
        if not person_id or not person_id.strip():
            return []
        person_id = person_id.strip()
        zone = zone.strip()
        room = (room or zone).strip()
        t = frame_epoch if frame_epoch is not None else time.time()
        now_iso = datetime.fromtimestamp(t, tz=timezone.utc).isoformat()

        with self._lock:
            # ---- classify posture from box ----
            posture = self._classify_posture(box)
            is_moving = motion_delta >= MOTION_MOVING_MIN
            is_stationary = motion_delta <= MOTION_STATIONARY_MAX

            # ---- determine activity type ----
            if is_moving:
                activity_type = "moving"
            elif posture == "standing":
                activity_type = "standing"
            elif posture == "sitting":
                activity_type = "sitting"
            else:
                activity_type = "stationary"

            # ---- sibling count in same zone ----
            sibling_count = self._sibling_count(person_id, zone)

            # ---- session key ----
            session_key = _slug(person_id, zone)
            session = self._sessions.get(session_key)

            emitted: list[dict[str, Any]] = []

            # ---- zone transition ----
            prev_zone = self._previous_zone.get(person_id)
            if prev_zone and prev_zone != zone:
                if zone and prev_zone:
                    emitted.append(self._make_event(
                        event_type="zone_changed",
                        type="zone_changed",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        confidence=CONFIDENCE_HIGH,
                        timestamp=t,
                        timestamp_iso=now_iso,
                        metadata={"from_zone": prev_zone, "to_zone": zone, "sibling_count": sibling_count},
                        support_signals=["zone_transition"],
                    ))
                if prev_zone and not zone:
                    emitted.append(self._make_event(
                        event_type="left_zone",
                        type="left_zone",
                        person_id=person_id,
                        track_id=track_id,
                        zone=None,
                        room=room,
                        confidence=CONFIDENCE_HIGH,
                        timestamp=t,
                        timestamp_iso=now_iso,
                        metadata={"from_zone": prev_zone, "sibling_count": sibling_count},
                        support_signals=["zone_transition"],
                    ))
                if zone and not prev_zone:
                    emitted.append(self._make_event(
                        event_type="entered_zone",
                        type="entered_zone",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        confidence=CONFIDENCE_HIGH,
                        timestamp=t,
                        timestamp_iso=now_iso,
                        metadata={"to_zone": zone, "sibling_count": sibling_count},
                        support_signals=["zone_transition"],
                    ))
                # Backward compat: keep moved_zone
                emitted.append(self._make_event(
                    event_type="moved_zone",
                    type="moved_zone",
                    person_id=person_id,
                    track_id=track_id,
                    zone=prev_zone,
                    room=(room if prev_zone else zone),
                    confidence=CONFIDENCE_HIGH,
                    timestamp=t,
                    timestamp_iso=now_iso,
                    metadata={"from_zone": prev_zone, "to_zone": zone, "sibling_count": sibling_count},
                    support_signals=["zone_transition"],
                ))
            self._previous_zone[person_id] = zone

            # ---- start or update session ----
            if session is None:
                session = SessionState(
                    session_id=session_key,
                    person_id=person_id,
                    track_id=track_id,
                    activity_type=activity_type,
                    zone=zone,
                    room=room,
                    started_at=t,
                    started_at_iso=now_iso,
                    confidence=CONFIDENCE_FLOOR,
                    support_signals=["first_observation"],
                )
                self._sessions[session_key] = session
                emitted.append(self._make_event(
                    event_type="activity_started",
                    type="activity_started",
                    person_id=person_id,
                    track_id=track_id,
                    zone=zone,
                    room=room,
                    activity_type=activity_type,
                    confidence=CONFIDENCE_FLOOR,
                    timestamp=t,
                    timestamp_iso=now_iso,
                    metadata={"sibling_count": sibling_count, "posture": posture},
                    support_signals=["session_start"],
                ))
                emitted.append(self._make_event(
                    event_type="appeared",
                    type="appeared",
                    person_id=person_id,
                    track_id=track_id,
                    zone=zone,
                    room=room,
                    confidence=CONFIDENCE_FLOOR,
                    timestamp=t,
                    timestamp_iso=now_iso,
                    metadata={"sibling_count": sibling_count, "posture": posture},
                    support_signals=["session_start"],
                ))

            # ---- update session ----
            dwell = t - session.started_at
            consistent = (session.activity_type == activity_type)
            conf_delta = CONFIDENCE_RAMP_PER_OBSERVATION if consistent else -0.03
            new_conf = min(CONFIDENCE_HIGH, max(CONFIDENCE_FLOOR, session.confidence + conf_delta))
            session.activity_type = activity_type
            session.zone = zone
            session.room = room
            session.confidence = new_conf
            session.last_observed_at = t
            session.last_observed_iso = now_iso
            session.event_count += 1
            if posture not in session.support_signals:
                session.support_signals.append(posture)

            # Track motion vs stationary durations
            if is_moving and session.last_motion_state != "moving":
                session.motion_started_at = t
                session.last_motion_state = "moving"
            elif is_stationary and session.last_motion_state != "stationary":
                session.stationary_started_at = t
                session.last_motion_state = "stationary"

            if session.last_motion_state == "moving":
                session.motion_duration = t - session.motion_started_at
            elif session.last_motion_state == "stationary":
                session.stationary_duration = t - session.stationary_started_at

            # persist updated session
            self._store.upsert_session(session)
            emitted.append(self._make_event(
                event_type="present",
                type="present",
                person_id=person_id,
                track_id=track_id,
                zone=zone,
                room=room,
                activity_type=activity_type,
                confidence=min(new_conf, 0.8),
                timestamp=t,
                timestamp_iso=now_iso,
                duration=dwell,
                metadata={"sibling_count": sibling_count, "posture": posture, "dwell_seconds": round(dwell, 1)},
                support_signals=["presence_update"],
            ))

            # ---- emit activity type event (once per observation) ----
            # Stationary is a MOTION signal, posture is a POSE signal.
            # A person can be standing + stationary, or sitting + stationary.
            # We emit the activity_type (based on posture) AND the stationary
            # event when motion is below threshold. No frame-spam because
            # these are orthogonal signals emitted once per observation cycle.
            if activity_type in {"standing", "sitting", "moving", "stationary"}:
                emitted.append(self._make_event(
                    event_type=activity_type,
                    type=activity_type,
                    person_id=person_id,
                    track_id=track_id,
                    zone=zone,
                    room=room,
                    activity_type=activity_type,
                    confidence=new_conf,
                    timestamp=t,
                    timestamp_iso=now_iso,
                    duration=dwell,
                    metadata={"sibling_count": sibling_count, "posture": posture, "dwell_seconds": round(dwell, 1)},
                    support_signals=[posture, "motion_delta:" + str(motion_delta)],
                ))

            # emit stationary separately when motion is low (orthogonal to posture)
            if is_stationary:
                emitted.append(self._make_event(
                    event_type="stationary",
                    type="stationary",
                    person_id=person_id,
                    track_id=track_id,
                    zone=zone,
                    room=room,
                    activity_type=activity_type,
                    confidence=new_conf,
                    timestamp=t,
                    timestamp_iso=now_iso,
                    duration=dwell,
                    metadata={"sibling_count": sibling_count, "posture": posture, "dwell_seconds": round(dwell, 1)},
                    support_signals=["stationary", "low_motion"],
                ))

            # ---- long sitting (only if sitting + dwell >= threshold) ----
            if activity_type == "sitting" and dwell >= LONG_SITTING_THRESHOLD_SECONDS:
                if "long_sitting" not in session.support_signals:
                    session.support_signals.append("long_sitting")
                    emitted.append(self._make_event(
                        event_type="long_sitting",
                        type="long_sitting",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        activity_type="sitting",
                        confidence=min(new_conf, 0.7),
                        timestamp=t,
                        timestamp_iso=now_iso,
                        duration=dwell,
                        metadata={"sibling_count": sibling_count, "dwell_seconds": round(dwell, 1), "posture": posture},
                        support_signals=["long_sitting", "sitting"],
                    ))

            # ---- inactivity (stationary + low motion + dwell >= threshold) ----
            if is_stationary and activity_type in {"stationary", "standing", "sitting"} and dwell >= LONG_INACTIVITY_THRESHOLD_SECONDS:
                if "inactivity" not in session.support_signals:
                    session.support_signals.append("inactivity")
                    emitted.append(self._make_event(
                        event_type="inactivity",
                        type="inactivity",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        activity_type=activity_type,
                        confidence=min(new_conf, 0.65),
                        timestamp=t,
                        timestamp_iso=now_iso,
                        duration=dwell,
                        metadata={"sibling_count": sibling_count, "dwell_seconds": round(dwell, 1), "posture": posture},
                        support_signals=["inactivity", "stationary"],
                    ))

            # ---- possible_phone_use: REQUIRES object evidence ----
            if activity_type == "sitting" and dwell >= PHONE_USE_DWELL:
                objects = [o.strip().lower() for o in (observed_objects or []) if o and o.strip()]
                associated_phone = any(label in PHONE_LABELS for label in objects)
                if associated_phone:
                    emitted.append(self._make_event(
                        event_type="possible_phone_use",
                        type="possible_phone_use",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        activity_type="sitting",
                        confidence=0.55,
                        timestamp=t,
                        timestamp_iso=now_iso,
                        duration=dwell,
                        metadata={
                            "sibling_count": sibling_count,
                            "dwell_seconds": round(dwell, 1),
                            "phone_evidence": True,
                            "observed_objects": objects,
                            "capability": PHONE_USE_CAPABILITY,
                            "posture": posture,
                        },
                        support_signals=["possible_phone_use", "sitting", "phone_object_associated"],
                    ))

            # ---- possible_tv_context: PROBABILISTIC only ----
            if (activity_type in {"sitting", "stationary"} or is_stationary) and zone in self.tv_context_zones:
                hour = _epoch_to_hour(t)
                evening = TV_EVENING_START <= hour <= TV_EVENING_END
                if evening:
                    emitted.append(self._make_event(
                        event_type="possible_tv_context",
                        type="possible_tv_context",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        activity_type=activity_type,
                        confidence=0.45,
                        timestamp=t,
                        timestamp_iso=now_iso,
                        duration=dwell,
                        metadata={
                            "sibling_count": sibling_count,
                            "dwell_seconds": round(dwell, 1),
                            "tv_zone": zone,
                            "evening_hour": hour,
                            "capability": TV_CONTEXT_CAPABILITY,
                            "deterministic": False,
                            "posture": posture,
                        },
                        support_signals=["possible_tv_context", "tv_zone", "evening"],
                    ))

            # ---- movement state with debounce ----
            motion_state = self._track_motion_state(person_id, is_moving, is_stationary, t,
                                                       zone=zone, room=room, track_id=track_id)

            # ---- posture transition detection ----
            prev_posture = self._previous_posture.get(person_id)
            if prev_posture is not None and prev_posture != posture and posture != "unknown":
                if prev_posture == "standing" and posture == "sitting":
                    evt = self._make_event(
                        event_type="stand_to_sit",
                        type="stand_to_sit",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        activity_type="sitting",
                        confidence=min(new_conf, 0.7),
                        timestamp=t,
                        timestamp_iso=now_iso,
                        duration=0.0,
                        metadata={"from_posture": prev_posture, "to_posture": posture},
                        support_signals=["posture_transition"],
                    )
                    emitted.append(evt)
                    self._store.add_event(evt)
                elif prev_posture == "sitting" and posture == "standing":
                    evt = self._make_event(
                        event_type="sit_to_stand",
                        type="sit_to_stand",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        activity_type="standing",
                        confidence=min(new_conf, 0.7),
                        timestamp=t,
                        timestamp_iso=now_iso,
                        duration=0.0,
                        metadata={"from_posture": prev_posture, "to_posture": posture},
                        support_signals=["posture_transition"],
                    )
                    emitted.append(evt)
                    self._store.add_event(evt)

            self._previous_posture[person_id] = posture

            # ---- long stationary ----
            if is_stationary and dwell >= LONG_STATIONARY_THRESHOLD_SECONDS:
                if "long_stationary" not in session.support_signals:
                    session.support_signals.append("long_stationary")
                    evt = self._make_event(
                        event_type="long_stationary",
                        type="long_stationary",
                        person_id=person_id,
                        track_id=track_id,
                        zone=zone,
                        room=room,
                        activity_type="stationary",
                        confidence=min(new_conf, 0.65),
                        timestamp=t,
                        timestamp_iso=now_iso,
                        duration=dwell,
                        metadata={"dwell_seconds": round(dwell, 1), "posture": posture},
                        support_signals=["long_stationary", "stationary"],
                    )
                    emitted.append(evt)
                    self._store.add_event(evt)

            # ---- persist emitted events to injected store ----
            for ev in emitted:
                self._store.add_event(ev)
            
            # ---- check habit triggers (auto-complete habits) ----
            for ev in emitted:
                try:
                    triggered = self._store.check_habit_trigger(ev)
                except Exception:
                    triggered = []
                # Auto-completed habits are noted but not emitted as events
                # to avoid polluting the activity timeline

            # ---- check prayer zone triggers (DND + lighting) ----
            for ev in emitted:
                try:
                    prayer_triggered = self._store.check_prayer_zone_trigger(ev)
                except Exception:
                    prayer_triggered = []
                # TODO: Integrate with reminder_rules / DND / lighting systems
                # For now, prayer zone triggers are logged
                for pt in prayer_triggered:
                    self._store.add_event({
                        "event_type": "prayer_zone_" + pt.get("action", "trigger"),
                        "person_id": ev.get("person_id", "unknown"),
                        "track_id": ev.get("track_id"),
                        "zone": pt.get("zone_name", ""),
                        "room": ev.get("room", ""),
                        "activity_type": "prayer_zone",
                        "confidence": 0.8,
                        "duration_seconds": 0.0,
                        "metadata": {
                            "dnd_duration_minutes": pt.get("dnd_duration_minutes"),
                            "lighting_scene": pt.get("lighting_scene"),
                        },
                    })

            return emitted

    def active_sessions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._session_to_dict(s) for s in self._sessions.values()]

    def expire_stale_sessions(self, stale_after_seconds: float = SESSION_STALE_SECONDS) -> list[dict[str, Any]]:
        """Expire sessions that have not been observed recently.

        Returns any activity_expired events emitted.
        """
        t = time.time()
        cutoff = t - stale_after_seconds
        expired: list[dict[str, Any]] = []
        with self._lock:
            to_remove = []
            for key, session in self._sessions.items():
                if session.last_observed_at < cutoff:
                    to_remove.append(key)
                    self._store.end_session(session.session_id, confidence=session.confidence)
                    # Emit disappeared event
                    last_zone = session.zone
                    if last_zone:
                        expired.append(self._make_event(
                            event_type="left_zone",
                            type="left_zone",
                            person_id=session.person_id,
                            track_id=session.track_id,
                            zone=None,
                            room=session.room,
                            confidence=CONFIDENCE_HIGH,
                            timestamp=t,
                            timestamp_iso=datetime.fromtimestamp(t, tz=timezone.utc).isoformat(),
                            duration=session.last_observed_at - session.started_at,
                            metadata={"from_zone": last_zone, "stale_seconds": round(t - session.last_observed_at, 1)},
                            support_signals=["zone_transition"],
                        ))
                    expired.append(self._make_event(
                        event_type="disappeared",
                        type="disappeared",
                        person_id=session.person_id,
                        track_id=session.track_id,
                        zone=last_zone,
                        room=session.room,
                        activity_type=session.activity_type,
                        confidence=session.confidence,
                        timestamp=t,
                        timestamp_iso=datetime.fromtimestamp(t, tz=timezone.utc).isoformat(),
                        duration=session.last_observed_at - session.started_at,
                        metadata={"stale_seconds": round(t - session.last_observed_at, 1)},
                        support_signals=["stale_timeout"],
                    ))
                    # Also emit activity_expired for backward compatibility
                    expired.append(self._make_event(
                        event_type="activity_expired",
                        type="activity_expired",
                        person_id=session.person_id,
                        track_id=session.track_id,
                        zone=last_zone,
                        room=session.room,
                        activity_type=session.activity_type,
                        confidence=session.confidence,
                        timestamp=t,
                        timestamp_iso=datetime.fromtimestamp(t, tz=timezone.utc).isoformat(),
                        duration=session.last_observed_at - session.started_at,
                        metadata={"stale_seconds": round(t - session.last_observed_at, 1)},
                        support_signals=["stale_timeout"],
                    ))
            for key in to_remove:
                del self._sessions[key]
        return expired

    def drain_events(self) -> list[dict[str, Any]]:
        """Drain any pending activity events into the store and rule pipeline.

        Called periodically by the background drain thread.
        Returns events that were emitted by expiring stale sessions.
        """
        expired = self.expire_stale_sessions()
        return expired

    def snapshot(self) -> dict[str, Any]:
        """Return a privacy-preserving summary snapshot.

        No camera/vision data is included. Only session metadata.
        """
        with self._lock:
            return {
                "timestamp": time.time(),
                "timestamp_iso": _now_iso(),
                "session_count": len(self._sessions),
                "sessions": [
                    {
                        "person_id": s.person_id,
                        "activity_type": s.activity_type,
                        "zone": s.zone,
                        "room": s.room,
                        "confidence": round(s.confidence, 3),
                        "started_at_iso": s.started_at_iso,
                        "duration_seconds": round(s.last_observed_at - s.started_at, 1),
                        "motion_duration": round(s.motion_duration, 1),
                        "stationary_duration": round(s.stationary_duration, 1),
                        "motion_state": s.last_motion_state,
                        "event_count": s.event_count,
                    }
                    for s in self._sessions.values()
                ],
                "phone_use_capability": PHONE_USE_CAPABILITY,
                "tv_context_capability": TV_CONTEXT_CAPABILITY,
                "pose_available": POSE_UNAVAILABLE,
            }

    # ------------------------------------------------------------------
    # Background thread lifecycle (threading.Event based)
    # ------------------------------------------------------------------

    def start_background_drain(self, interval_seconds: float = 2.0) -> dict[str, Any]:
        with self._lock:
            if self._drain_thread is not None and self._drain_thread.is_alive():
                return {"status": "already_running"}
            self._drain_stop.clear()
            self._drain_thread = threading.Thread(
                target=self._drain_loop,
                args=(interval_seconds,),
                daemon=True,
                name="HAI-drain",
            )
            self._drain_thread.start()
            return {"status": "started", "interval_seconds": interval_seconds}

    def stop_background_drain(self, timeout: float = 5.0) -> dict[str, Any]:
        with self._lock:
            self._drain_stop.set()
            if self._drain_thread is not None:
                self._drain_thread.join(timeout=timeout)
            self._drain_thread = None
            return {"status": "stopped"}

    def start_snapshot_scheduler(self, interval_seconds: float = 300.0) -> dict[str, Any]:
        with self._lock:
            if self._snapshot_thread is not None and self._snapshot_thread.is_alive():
                return {"status": "already_running"}
            self._snapshot_stop.clear()
            self._snapshot_thread = threading.Thread(
                target=self._snapshot_loop,
                args=(interval_seconds,),
                daemon=True,
                name="HAI-snapshot",
            )
            self._snapshot_thread.start()
            return {"status": "started", "interval_seconds": interval_seconds}

    def stop_snapshot_scheduler(self, timeout: float = 5.0) -> dict[str, Any]:
        with self._lock:
            self._snapshot_stop.set()
            if self._snapshot_thread is not None:
                self._snapshot_thread.join(timeout=timeout)
            self._snapshot_thread = None
            return {"status": "stopped"}

    # ------------------------------------------------------------------
    # Pattern learning scheduler
    # ------------------------------------------------------------------

    def start_pattern_learner(self, interval_seconds: float = 300.0) -> dict[str, Any]:
        """Start periodic pattern rebuild + suggestion generation.

        Runs in a background daemon thread. Rebuilds patterns from
        recent activity events and generates new rule suggestions.
        """
        with self._lock:
            if self._pattern_thread is not None and self._pattern_thread.is_alive():
                return {"status": "already_running"}
            self._pattern_stop.clear()
            self._pattern_thread = threading.Thread(
                target=self._pattern_loop,
                args=(interval_seconds,),
                daemon=True,
                name="HAI-pattern",
            )
            self._pattern_thread.start()
            return {"status": "started", "interval_seconds": interval_seconds}

    def stop_pattern_learner(self, timeout: float = 5.0) -> dict[str, Any]:
        with self._lock:
            self._pattern_stop.set()
            if self._pattern_thread is not None:
                self._pattern_thread.join(timeout=timeout)
            self._pattern_thread = None
            return {"status": "stopped"}

    def _pattern_loop(self, interval: float) -> None:
        while not self._pattern_stop.wait(interval):
            try:
                from .pattern_learner import rebuild_patterns, generate_rule_suggestions
                rebuild_patterns(store=self._store)
                generate_rule_suggestions(store=self._store)
            except Exception:
                pass

    def _track_motion_state(self, person_id, is_moving, is_stationary, t,
                            zone=None, room=None, track_id=None) -> str:
        """Track moving/stationary state with debounce.

        Returns current motion_state ('moving' or 'stationary').
        Requires MOVEMENT_DEBOUNCE_FRAMES consecutive frames to switch.
        Emits movement_started / movement_stopped events on transitions.
        """
        prev_state = self._previous_motion_state.get(person_id, "stationary")
        count = self._motion_frame_count.get(person_id, 0)

        # Count consecutive frames where the *desired* state matches the input
        # This accumulates regardless of current motion_state, allowing the
        # debounce to complete after MOVEMENT_DEBOUNCE_FRAMES frames.
        if is_moving:
            # Increment if we're seeing moving frames (regardless of current state)
            new_count = count + 1 if prev_state == "moving" else count + 1
        elif is_stationary:
            new_count = count + 1 if prev_state == "stationary" else count + 1
        else:
            new_count = 0

        new_state = prev_state
        if new_count >= MOVEMENT_DEBOUNCE_FRAMES:
            if is_moving:
                new_state = "moving"
            elif is_stationary:
                new_state = "stationary"
            if new_state != prev_state:
                self._previous_motion_state[person_id] = new_state
                self._motion_frame_count[person_id] = 0
                # Emit transition event
                event_type = "movement_started" if new_state == "moving" else "movement_stopped"
                self._store.add_event({
                    "event_type": event_type,
                    "type": event_type,
                    "person_id": person_id,
                    "track_id": track_id,
                    "zone": zone or "",
                    "room": room or "",
                    "activity_type": new_state,
                    "confidence": CONFIDENCE_HIGH,
                    "timestamp": t,
                    "duration": 0.0,
                    "metadata": {"from_state": prev_state, "to_state": new_state},
                    "support_signals": ["motion_debounce"],
                })
            else:
                self._motion_frame_count[person_id] = new_count
        else:
            self._motion_frame_count[person_id] = new_count

        return new_state

    @staticmethod
    def _classify_posture(box: list[float] | None) -> str:
        """Classify standing vs sitting from box height/width ratio.

        Tall box → standing context.
        Short/wide box → sitting context.
        No box → unknown.
        """
        if not box or len(box) < 4:
            return "unknown"
        x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
        height = max(abs(y2 - y1), 1.0)
        width = max(abs(x2 - x1), 1.0)
        ratio = height / width
        if ratio >= STANDING_HEIGHT_RATIO_MIN:
            return "standing"
        if ratio <= SITTING_HEIGHT_RATIO_MAX:
            return "sitting"
        # middle ground — lean on height
        if height > width:
            return "standing"
        return "sitting"

    def _sibling_count(self, person_id: str, zone: str) -> int:
        """Count other currently-active people in the same zone."""
        count = 0
        for s in self._sessions.values():
            if s.person_id != person_id and s.zone == zone:
                count += 1
        return count

    @staticmethod
    def _make_event(
        *,
        event_type: str,
        type: str,
        person_id: str,
        track_id: str | None,
        zone: Any = "",
        room: Any = "",
        activity_type: str = "",
        confidence: float,
        timestamp: float,
        timestamp_iso: str,
        duration: float = 0.0,
        metadata: dict[str, Any] | None = None,
        support_signals: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "event_type": event_type,
            "type": type,
            "person_id": person_id,
            "track_id": track_id,
            "zone": zone,
            "room": room,
            "activity_type": activity_type,
            "confidence": round(confidence, 3),
            "timestamp": timestamp,
            "timestamp_iso": timestamp_iso,
            "duration": round(duration, 1),
            "metadata": metadata or {},
            "support_signals": support_signals or [],
        }

    @staticmethod
    def _session_to_dict(session: SessionState) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "person_id": session.person_id,
            "track_id": session.track_id,
            "activity_type": session.activity_type,
            "zone": session.zone,
            "room": session.room,
            "started_at": session.started_at,
            "started_at_iso": session.started_at_iso,
            "confidence": session.confidence,
            "event_count": session.event_count,
            "support_signals": session.support_signals,
            "last_observed_at": session.last_observed_at,
            "last_observed_iso": session.last_observed_iso,
            "motion_duration": round(session.motion_duration, 1),
            "stationary_duration": round(session.stationary_duration, 1),
            "motion_state": session.last_motion_state,
        }

    # ------------------------------------------------------------------
    # Background loops
    # ------------------------------------------------------------------

    def _drain_loop(self, interval: float) -> None:
        while not self._drain_stop.wait(interval):
            try:
                self.drain_events()
            except Exception:
                pass

    def _snapshot_loop(self, interval: float) -> None:
        while not self._snapshot_stop.wait(interval):
            try:
                if self._store.get_setting("snapshot_enabled") in {"1", "true", "yes"}:
                    snapshot = self.snapshot()
                    self._store.save_snapshot(snapshot)
            except Exception:
                pass


# ------------------------------------------------------------------
# Pose provider abstraction
# ------------------------------------------------------------------
POSE_CAPABILITY_AVAILABLE = "AVAILABLE"
POSE_CAPABILITY_NOT_CONFIGURED = "NOT_CONFIGURED"


class PoseProvider:
    """Optional pose estimation provider.

    Detects a compatible local pose model at startup. If available,
    provides low-FPS sitting/standing classification. If not, returns
    unknown_posture. Never auto-downloads large models.
    """

    def __init__(self) -> None:
        self.model = None
        self._capability = POSE_CAPABILITY_NOT_CONFIGURED

    def available(self) -> bool:
        """Check if a usable pose model is available locally."""
        try:
            from .pose_backend import resolve_pose_model
            model = resolve_pose_model()
            if model is not None:
                self.model = model
                self._capability = POSE_CAPABILITY_AVAILABLE
                return True
        except Exception:
            pass
        self._capability = POSE_CAPABILITY_NOT_CONFIGURED
        return False

    def estimate(self, frame) -> str | None:
        """Estimate posture from frame. Returns 'sitting' or 'standing' or None.

        Returns None when no pose model is available (unknown_posture).
        """
        if self.model is None or self._capability != POSE_CAPABILITY_AVAILABLE:
            return None
        try:
            return self.model.estimate_posture(frame)
        except Exception:
            return None

    @property
    def capability(self) -> str:
        return self._capability


def resolve_pose_provider() -> PoseProvider:
    """Create and probe a PoseProvider.

    Returns a provider that may or may not have a model.
    """
    provider = PoseProvider()
    provider.available()
    return provider


# ------------------------------------------------------------------
# Module-level singleton (used by routes)
# ------------------------------------------------------------------

human_activity_intelligence = HumanActivityIntelligence()
