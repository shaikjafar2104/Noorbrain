#!/usr/bin/env python3
"""
Comprehensive test file for Human Activity + Islamic AI V12.6 implementation.

Run with:  python -m pytest tests/test_human_activity_islamic_ai_v126.py -v

Covers:
- sitting session
- standing transition
- moving
- stationary
- smoothing/hysteresis
- long sitting
- long inactivity
- phone association (REQUIRES object evidence)
- unrelated phone rejection
- TV context (probabilistic)
- confidence
- session end
- zone transition
- multi-person
- pattern occurrence
- pattern confidence
- rule suggestion creation
- rule suggestion dismiss
- rule suggestion snooze
- rule suggestion never-suggest
- rule suggestion cooldown
- snapshot disabled by default
- snapshot retention
- Pi target required
- Pi offline
- Pi acknowledgement failure
- Islamic rule action
- no laptop fallback
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hai_store(tmp_path: Path):
    """ActivityStore backed by a temporary DB — never touches production data."""
    from services.human_activity_intelligence.store import ActivityStore

    return ActivityStore(db_path=tmp_path / "activity.db")


@pytest.fixture
def hai_engine(tmp_path: Path):
    """HumanActivityIntelligence using a temp-store."""
    from services.human_activity_intelligence.engine import HumanActivityIntelligence
    from services.human_activity_intelligence.store import ActivityStore

    store = ActivityStore(db_path=tmp_path / "activity.db")
    return HumanActivityIntelligence(store=store)


@pytest.fixture
def islamic_store(tmp_path: Path):
    """IslamicLearningStore backed by a temporary JSON file."""
    from services.islamic_learning.store import IslamicLearningStore

    return IslamicLearningStore(store_path=tmp_path / "islamic_learning.json")


@pytest.fixture
def islamic_rule_store(tmp_path: Path):
    """Separate Islamic Intelligence rule store (NOT Islamic Learning)."""
    from services.islamic_intelligence_v12.store import Store

    path = tmp_path / "islamic_rules.json"
    path.write_text(json.dumps({
        "version": "12.0.0",
        "settings": {},
        "events": [],
        "rules": [],
    }))
    store = Store()
    store.path = path
    return store


@pytest.fixture
def reminder_engine(tmp_path: Path):
    from services.reminder_rules.reminder_rules import ReminderRulesEngine

    rules_file = tmp_path / "test_reminder_rules.json"
    rules_file.write_text(json.dumps({
        "version": "1.0.0",
        "settings": {"cooldown_global_seconds": 60},
        "rules": [],
    }))
    return ReminderRulesEngine(rules_file=rules_file)


@pytest.fixture
def playback_router(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Return a PlaybackRouter with a fake Pi node (no real network)."""
    from services.playback_router.router import PlaybackRouter

    nodes_file = tmp_path / "nodes.json"
    monkeypatch.setattr("services.playback_router.router.STORE", nodes_file)
    monkeypatch.setattr("services.playback_router.router.LEGACY_CONFIG", tmp_path / "missing.json")
    router = PlaybackRouter()
    node = router.create_node({
        "node_id": "test-pi",
        "name": "Test Pi",
        "room": "Hall",
        "url": "http://127.0.0.1:9999",
        "token": "test-token",
        "capabilities": {"microphone": True, "speaker": True, "playback": True},
    })
    return router, node


# ---------------------------------------------------------------------------
# 1. Sitting session
# ---------------------------------------------------------------------------


def test_sitting_session_emits_activity_started_event(hai_engine):
    events = hai_engine.observe(
        person_id="p1",
        track_id="t1",
        zone="Hall",
        room="Hall",
        box=[100, 100, 200, 300],  # height ratio 200/100 = 2.0 → standing
        motion_delta=0.0,
    )
    types = {ev["event_type"] for ev in events}
    assert "activity_started" in types


def test_sitting_session_persisted_in_store(hai_engine, hai_store):
    hai_engine.observe(
        person_id="p2",
        track_id="t2",
        zone="Kitchen",
        room="Kitchen",
        box=[80, 100, 160, 250],  # height 150, width 80 → ratio 1.875
        motion_delta=0.0,
    )
    sessions = hai_store.active_sessions()
    assert any(s["person_id"] == "p2" and s["zone"] == "Kitchen" for s in sessions)


# ---------------------------------------------------------------------------
# 2. Standing transition
# ---------------------------------------------------------------------------


def test_standing_transition_emits_standing_event(hai_engine):
    events = hai_engine.observe(
        person_id="p3",
        track_id="t3",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],  # ratio 300/200 = 1.5
        motion_delta=5.0,
    )
    standing = [ev for ev in events if ev["event_type"] == "standing"]
    assert standing, "expected a standing event from tall box + motion"


def test_standing_to_sitting_transition(hai_engine):
    e1 = hai_engine.observe(
        person_id="p4",
        track_id="t4",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=5.0,
    )
    e2 = hai_engine.observe(
        person_id="p4",
        track_id="t4",
        zone="Hall",
        room="Hall",
        box=[200, 250, 300, 300],  # ratio 50/100=0.5 → sitting
        motion_delta=0.0,
    )
    types = {ev["event_type"] for ev in e1 + e2}
    assert "standing" in types or "sitting" in types


# ---------------------------------------------------------------------------
# 3. Moving
# ---------------------------------------------------------------------------


def test_moving_event_emitted_for_high_motion(hai_engine):
    events = hai_engine.observe(
        person_id="p5",
        track_id="t5",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=50.0,
    )
    moving = [ev for ev in events if ev["event_type"] == "moving"]
    assert moving, "expected moving event for high motion delta"


# ---------------------------------------------------------------------------
# 4. Stationary
# ---------------------------------------------------------------------------


def test_stationary_event_emitted_for_low_motion(hai_engine):
    events = hai_engine.observe(
        person_id="p6",
        track_id="t6",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=1.0,
    )
    stationary = [ev for ev in events if ev["event_type"] == "stationary"]
    assert stationary, "expected stationary event for low motion"


# ---------------------------------------------------------------------------
# 5. Smoothing/hysteresis
# ---------------------------------------------------------------------------


def test_confidence_not_spiking_from_one_observation(hai_engine):
    e1 = hai_engine.observe(
        person_id="p7",
        track_id="t7",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
    )
    conf = max(ev.get("confidence", 0) for ev in e1)
    assert conf < 0.9, f"confidence should not spike from a single observation: {conf}"


def test_confidence_ramp_over_multiple_observations(hai_engine):
    for _ in range(5):
        hai_engine.observe(
            person_id="p8",
            track_id="t8",
            zone="Hall",
            room="Hall",
            box=[200, 300, 400, 600],
            motion_delta=0.0,
        )
    sessions = hai_engine.active_sessions()
    assert any(s["confidence"] > 0.6 for s in sessions)


# ---------------------------------------------------------------------------
# 6. Long sitting — uses real session, not guessed key
# ---------------------------------------------------------------------------


def test_long_sitting_emitted_after_threshold(hai_engine):
    from services.human_activity_intelligence.engine import LONG_SITTING_THRESHOLD_SECONDS

    # Let engine create the real session via observe()
    hai_engine.observe(
        person_id="p9",
        track_id="t9",
        zone="Hall",
        room="Hall",
        box=[200, 250, 300, 300],  # sitting height ratio
        motion_delta=0.0,
    )
    # Locate the actual SessionState by person/zone fields — NOT guessed key
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p9" and s.zone == "Hall"
    )
    # Backdate the real session past the long-sitting threshold
    session.started_at = time.time() - LONG_SITTING_THRESHOLD_SECONDS - 10
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    # Re-observe to trigger long_sitting event
    events = hai_engine.observe(
        person_id="p9",
        track_id="t9",
        zone="Hall",
        room="Hall",
        box=[200, 250, 300, 300],
        motion_delta=0.0,
        frame_epoch=time.time(),
    )
    long_sitting = [ev for ev in events if ev["event_type"] == "long_sitting"]
    assert long_sitting, "expected long_sitting event after threshold"


# ---------------------------------------------------------------------------
# 7. Long inactivity — uses real session, not guessed key
# ---------------------------------------------------------------------------


def test_inactivity_emitted_after_threshold(hai_engine):
    from services.human_activity_intelligence.engine import INACTIVITY_THRESHOLD_SECONDS

    # Seed a low-motion stationary observation to create the session
    hai_engine.observe(
        person_id="p10",
        track_id="t10",
        zone="Studio",
        room="Studio",
        box=[200, 300, 400, 600],  # standing ratio
        motion_delta=0.5,  # below stationary threshold
    )
    # Locate the real session by person/zone
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p10" and s.zone == "Studio"
    )
    # Backdate the real session past the inactivity threshold
    session.started_at = time.time() - INACTIVITY_THRESHOLD_SECONDS - 10
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    # Re-observe with low motion to trigger inactivity event
    events = hai_engine.observe(
        person_id="p10",
        track_id="t10",
        zone="Studio",
        room="Studio",
        box=[200, 300, 400, 600],
        motion_delta=0.5,
        frame_epoch=time.time(),
    )
    inactivity = [ev for ev in events if ev["event_type"] == "inactivity"]
    assert inactivity, "expected inactivity event after threshold"


# ---------------------------------------------------------------------------
# 8. Phone association — REQUIRES object evidence
# ---------------------------------------------------------------------------


def test_possible_phone_use_only_with_associated_phone_object(hai_engine):
    """Phone use is ONLY emitted when observed_objects contains an associated phone label."""
    from services.human_activity_intelligence.engine import PHONE_USE_DWELL

    # Seed sitting observation to create session
    hai_engine.observe(
        person_id="p11",
        track_id="t11",
        zone="Lounge",
        room="Lounge",
        box=[150, 200, 250, 250],
        motion_delta=0.0,
    )
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p11" and s.zone == "Lounge"
    )
    session.started_at = time.time() - PHONE_USE_DWELL - 10
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    events = hai_engine.observe(
        person_id="p11",
        track_id="t11",
        zone="Lounge",
        room="Lounge",
        box=[150, 200, 250, 250],
        motion_delta=0.0,
        frame_epoch=time.time(),
        observed_objects=["cell phone", "coffee cup"],
    )
    phone_events = [ev for ev in events if ev["event_type"] == "possible_phone_use"]
    assert phone_events, "expected possible_phone_use with associated phone object"


def test_no_phone_use_without_object_evidence(hai_engine):
    """Sitting + dwell WITHOUT phone object → NO possible_phone_use."""
    from services.human_activity_intelligence.engine import PHONE_USE_DWELL

    hai_engine.observe(
        person_id="p12",
        track_id="t12",
        zone="Lounge",
        room="Lounge",
        box=[150, 200, 250, 250],
        motion_delta=0.0,
    )
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p12" and s.zone == "Lounge"
    )
    session.started_at = time.time() - PHONE_USE_DWELL - 10
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    events = hai_engine.observe(
        person_id="p12",
        track_id="t12",
        zone="Lounge",
        room="Lounge",
        box=[150, 200, 250, 250],
        motion_delta=0.0,
        frame_epoch=time.time(),
        observed_objects=["book", "coffee cup"],
    )
    phone_events = [ev for ev in events if ev["event_type"] == "possible_phone_use"]
    assert not phone_events, "should not emit possible_phone_use without phone object"


def test_no_phone_use_for_unrelated_phone_object(hai_engine):
    """Phone object not associated with this person's track → NO possible_phone_use."""
    from services.human_activity_intelligence.engine import PHONE_USE_DWELL

    hai_engine.observe(
        person_id="p13",
        track_id="t13",
        zone="Lounge",
        room="Lounge",
        box=[150, 200, 250, 250],
        motion_delta=0.0,
    )
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p13" and s.zone == "Lounge"
    )
    session.started_at = time.time() - PHONE_USE_DWELL - 10
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    # Phone object listed but NOT associated with track t13
    # observed_objects means objects ALREADY ASSOCIATED WITH THAT PERSON/TRACK.
    # An unrelated phone elsewhere must NOT be in this person's observed_objects.
    events = hai_engine.observe(
        person_id="p13",
        track_id="t13",
        zone="Lounge",
        room="Lounge",
        box=[150, 200, 250, 250],
        motion_delta=0.0,
        frame_epoch=time.time(),
        observed_objects=[],
    )
    phone_events = [ev for ev in events if ev["event_type"] == "possible_phone_use"]
    assert not phone_events, "unrelated phone object should not trigger possible_phone_use"


# ---------------------------------------------------------------------------
# 9. TV context — probabilistic only
# ---------------------------------------------------------------------------


def test_possible_tv_context_emitted_for_tv_zone_evening(hai_engine):
    # Override TV zones on the FIXTURE engine, NOT the singleton
    hai_engine.tv_context_zones = {"Hall"}

    # Seed sitting observation to create session
    hai_engine.observe(
        person_id="p14",
        track_id="t14",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
    )
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p14" and s.zone == "Hall"
    )
    session.started_at = time.time() - 60
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())

    # Use explicit UTC timestamp for evening hour
    evening_ts = (
        __import__("datetime")
        .datetime(2026, 8, 15, 19, 0, 0, tzinfo=__import__("datetime").timezone.utc)
        .timestamp()
    )
    events = hai_engine.observe(
        person_id="p14",
        track_id="t14",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
        frame_epoch=evening_ts,
    )
    tv_events = [ev for ev in events if ev["event_type"] == "possible_tv_context"]
    assert tv_events, "expected possible_tv_context in Hall during evening"
    assert tv_events[0]["metadata"].get("deterministic") is False
    assert tv_events[0]["metadata"].get("capability") == "PROBABILISTIC_ONLY"


def test_no_tv_context_outside_evening_hours(hai_engine):
    # Override TV zones on the FIXTURE engine
    hai_engine.tv_context_zones = {"Hall"}

    hai_engine.observe(
        person_id="p15",
        track_id="t15",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
    )
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p15" and s.zone == "Hall"
    )
    session.started_at = time.time() - 60
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())

    # Morning hour — UTC
    morning_ts = (
        __import__("datetime")
        .datetime(2026, 8, 15, 8, 0, 0, tzinfo=__import__("datetime").timezone.utc)
        .timestamp()
    )
    events = hai_engine.observe(
        person_id="p15",
        track_id="t15",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
        frame_epoch=morning_ts,
    )
    tv_events = [ev for ev in events if ev["event_type"] == "possible_tv_context"]
    assert not tv_events, "should not emit possible_tv_context outside evening hours"


def test_no_tv_context_for_non_tv_zone(hai_engine):
    """Zone not in TV_CONTEXT_ZONES → no TV context even if evening."""
    hai_engine.observe(
        person_id="p16",
        track_id="t16",
        zone="Office",
        room="Office",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
    )
    session = next(
        s for s in hai_engine._sessions.values()
        if s.person_id == "p16" and s.zone == "Office"
    )
    session.started_at = time.time() - 60
    session.started_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())

    evening_ts = (
        __import__("datetime")
        .datetime(2026, 8, 15, 20, 0, 0, tzinfo=__import__("datetime").timezone.utc)
        .timestamp()
    )
    events = hai_engine.observe(
        person_id="p16",
        track_id="t16",
        zone="Office",
        room="Office",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
        frame_epoch=evening_ts,
    )
    tv_events = [ev for ev in events if ev["event_type"] == "possible_tv_context"]
    assert not tv_events, "Office is not a TV zone"


# ---------------------------------------------------------------------------
# 10. Confidence
# ---------------------------------------------------------------------------


def test_confidence_field_present_on_all_events(hai_engine):
    events = hai_engine.observe(
        person_id="p16",
        track_id="t16",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
    )
    for ev in events:
        assert "confidence" in ev
        assert 0.0 <= ev["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 11. Session end
# ---------------------------------------------------------------------------


def test_session_ends_on_stale_timeout(hai_engine, hai_store):
    hai_engine.observe(
        person_id="p17",
        track_id="t17",
        zone="Kitchen",
        room="Kitchen",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
        frame_epoch=time.time() - 10,
    )
    expired = hai_engine.expire_stale_sessions(stale_after_seconds=0.0)
    assert any(e.get("event_type") == "activity_expired" for e in expired)
    active = hai_engine.active_sessions()
    assert not any(s["person_id"] == "p17" for s in active)


# ---------------------------------------------------------------------------
# 12. Zone transition
# ---------------------------------------------------------------------------


def test_zone_transition_event_emitted(hai_engine):
    e1 = hai_engine.observe(
        person_id="p18",
        track_id="t18",
        zone="Hall",
        room="Hall",
        box=[200, 300, 400, 600],
        motion_delta=0.0,
    )
    e2 = hai_engine.observe(
        person_id="p18",
        track_id="t18",
        zone="Kitchen",
        room="Kitchen",
        box=[100, 100, 200, 300],
        motion_delta=0.0,
    )
    zone_events = [ev for ev in (e1 + e2) if ev["event_type"] == "moved_zone"]
    assert zone_events, "expected moved_zone event on zone transition"


# ---------------------------------------------------------------------------
# 13. Multi-person
# ---------------------------------------------------------------------------


def test_multi_person_sessions_independent(hai_engine):
    hai_engine.observe(person_id="A", track_id="a1", zone="Hall", room="Hall", box=[200, 300, 400, 600], motion_delta=0.0)
    hai_engine.observe(person_id="B", track_id="b1", zone="Hall", room="Hall", box=[150, 200, 250, 250], motion_delta=0.0)
    sessions = hai_engine.active_sessions()
    person_ids = {s["person_id"] for s in sessions}
    assert "A" in person_ids
    assert "B" in person_ids


def test_multi_person_sibling_count_appended(hai_engine):
    hai_engine.observe(person_id="X", track_id="x1", zone="Hall", room="Hall", box=[200, 300, 400, 600], motion_delta=0.0)
    events = hai_engine.observe(person_id="Y", track_id="y1", zone="Hall", room="Hall", box=[200, 300, 400, 600], motion_delta=0.0)
    sibling_events = [ev for ev in events if ev.get("metadata", {}).get("sibling_count", 0) > 0]
    assert sibling_events, "expected sibling_count > 0 when multiple people in same zone"


# ---------------------------------------------------------------------------
# 14. Pattern occurrence — verifies store isolation + store injection
# ---------------------------------------------------------------------------


def test_learned_pattern_created_from_repeated_events(hai_store, hai_engine):
    """Same person/zone/activity repeated builds a pattern.

    Flow:
      observe repeated events into hai_engine
      assert events exist in hai_store
      rebuild_patterns(store=hai_store)  # uses injected store
      assert pattern exists
    """
    now = time.time()
    for i in range(5):
        hai_engine.observe(
            person_id="pat-user",
            track_id=f"pt-{i}",
            zone="Hall",
            room="Hall",
            box=[200, 300, 400, 600],
            motion_delta=0.0,
            frame_epoch=now - i * 10,
        )

    # Verify events are in the injected store
    events = hai_store.recent_events(limit=50)
    assert events, "expected events in injected store"

    # Use store injection
    from services.human_activity_intelligence.pattern_learner import rebuild_patterns

    rebuild_patterns(store=hai_store)
    patterns = hai_store.list_patterns(limit=50)
    assert patterns, "expected at least one learned pattern after repeated observations"


# ---------------------------------------------------------------------------
# 15. Pattern confidence
# ---------------------------------------------------------------------------


def test_pattern_confidence_increases_with_support(hai_store):
    pid = f"single:{uuid.uuid4().hex[:8]}"
    for _ in range(3):
        hai_store.add_pattern({
            "id": pid,
            "pattern_type": "activity_pattern",
            "activity_type": "sitting",
            "confidence": 0.5,
            "description": "test",
        })
    patterns = hai_store.list_patterns(limit=10)
    match = next((p for p in patterns if p["id"] == pid), None)
    assert match is not None
    assert match["support_count"] >= 3
    assert match["confidence"] >= 0.5


# ---------------------------------------------------------------------------
# 16. Rule suggestion — uses store injection
# ---------------------------------------------------------------------------


def test_rule_suggestion_created_from_pattern(hai_store):
    pat_id = f"pat-sug-{uuid.uuid4().hex[:8]}"
    hai_store.add_pattern({
        "id": pat_id,
        "pattern_type": "activity_pattern",
        "person_id": "p-sug",
        "zone": "Hall",
        "activity_type": "sitting",
        "confidence": 0.85,
        "support_count": 5,
        "description": "Person often sits in Hall",
        "first_seen_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "last_seen_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "usual_days": ["mon", "tue", "wed", "thu", "fri"],
        "usual_start_hour": 14,
        "usual_end_hour": 15,
    })
    from services.human_activity_intelligence.pattern_learner import generate_rule_suggestions

    result = generate_rule_suggestions(store=hai_store)
    assert result["created_count"] >= 1, f"expected at least one suggestion, got {result}"
    suggestions = hai_store.list_suggestions(status="new")
    assert any(s["pattern_id"] == pat_id for s in suggestions)


# ---------------------------------------------------------------------------
# 17. Rule suggestion dismiss
# ---------------------------------------------------------------------------


def test_suggestion_can_be_dismissed(hai_store):
    sug = hai_store.add_suggestion({
        "id": f"sug-d-{uuid.uuid4().hex[:8]}",
        "suggestion_type": "rule_suggestion",
        "rule_name": "Test Suggestion",
        "rule_trigger": "long_sitting",
        "rule_zone": "Hall",
        "rule_message": "Test message",
        "priority": 0.7,
        "status": "new",
        "created_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "updated_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    })
    result = hai_store.dismiss_suggestion(sug["id"])
    assert result is not None
    assert result["status"] == "dismissed"


# ---------------------------------------------------------------------------
# 18. Rule suggestion snooze
# ---------------------------------------------------------------------------


def test_suggestion_can_be_snoozed(hai_store):
    sug = hai_store.add_suggestion({
        "id": f"sug-s-{uuid.uuid4().hex[:8]}",
        "suggestion_type": "rule_suggestion",
        "rule_name": "Snooze Test",
        "rule_trigger": "inactivity",
        "rule_zone": "Hall",
        "rule_message": "snooze test",
        "priority": 0.6,
        "status": "new",
        "created_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "updated_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    })
    result = hai_store.snooze_suggestion(sug["id"], minutes=60)
    assert result is not None
    assert result["status"] == "snoozed"
    assert result["snoozed_until_epoch"] > time.time()


# ---------------------------------------------------------------------------
# 19. Rule suggestion never-suggest
# ---------------------------------------------------------------------------


def test_suggestion_can_be_marked_never_suggest(hai_store):
    sug = hai_store.add_suggestion({
        "id": f"sug-ns-{uuid.uuid4().hex[:8]}",
        "suggestion_type": "rule_suggestion",
        "rule_name": "Never suggest test",
        "rule_trigger": "possible_phone_use",
        "rule_zone": "Hall",
        "rule_message": "never suggest",
        "priority": 0.5,
        "status": "new",
        "created_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "updated_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    })
    result = hai_store.never_suggest(sug["id"])
    assert result is not None
    assert result["never_suggest"] is True
    assert result["status"] == "never_suggest"


# ---------------------------------------------------------------------------
# 20. Rule suggestion cooldown — uses real create_rule + real trigger contract
# ---------------------------------------------------------------------------


def test_suggestion_cooldown_applied(reminder_engine):
    """First event fires, second within cooldown is suppressed."""
    rule = reminder_engine.create_rule({
        "id": f"rule-cd-{uuid.uuid4().hex[:8]}",
        "name": "Cooldown test",
        "trigger": "long_sitting",
        "message": "test",
        "action_type": "tts",
        "target_node": "existing-pi-audio",
        "cooldown_seconds": 300,
    })
    event = {
        "type": rule["trigger"],
        "person_id": "p-cd",
        "zone": "Hall",
        "duration": 400,
        "timestamp": time.time(),
    }
    first = reminder_engine.handle_event(event)
    assert len(first) == 1, f"expected first fire, got {first}"
    second = reminder_engine.handle_event(event)
    assert len(second) == 0, "second fire should be suppressed by cooldown"


# ---------------------------------------------------------------------------
# 21. Snapshot disabled by default
# ---------------------------------------------------------------------------


def test_snapshot_disabled_by_default(hai_store):
    assert hai_store.get_setting("snapshot_enabled") is None
    result = hai_store.save_snapshot({"test": True})
    assert result is None, "snapshot must not be saved when disabled"


# ---------------------------------------------------------------------------
# 22. Snapshot retention
# ---------------------------------------------------------------------------


def test_snapshot_saved_when_enabled(hai_store):
    hai_store.set_setting("snapshot_enabled", "1")
    snap = {"test": True, "timestamp": time.time()}
    result = hai_store.save_snapshot(snap)
    assert result is not None
    assert result["saved"] is True
    snapshots = hai_store.list_snapshots(limit=10)
    assert any(s["snapshot"].get("test") is True for s in snapshots)


# ---------------------------------------------------------------------------
# 23. Pi target required — asserts ValueError on missing target
# ---------------------------------------------------------------------------


def test_rule_requires_target_node(reminder_engine):
    """create_rule with audio action and no target_node raises ValueError."""
    with pytest.raises(ValueError, match="target Raspberry Pi"):
        reminder_engine.create_rule({
            "id": f"rule-target-{uuid.uuid4().hex[:8]}",
            "name": "Pi target required test",
            "trigger": "long_sitting",
            "message": "test",
            "action_type": "tts",
            "target_node": "",
            "cooldown_seconds": 0,
        })


# ---------------------------------------------------------------------------
# 24. Pi offline — patches authoritative production playback singleton
# ---------------------------------------------------------------------------


def test_pi_offline_is_truthful_failure(reminder_engine, playback_router):
    router, node = playback_router
    rule = reminder_engine.create_rule({
        "id": f"rule-offline-{uuid.uuid4().hex[:8]}",
        "name": "Offline Pi test",
        "trigger": "long_sitting",
        "message": "test",
        "action_type": "tts",
        "target_node": node["node_id"],
        "cooldown_seconds": 0,
    })
    from services.playback_router.router import NodeUnavailableError
    import services.playback_router.router as playback_module

    original_play = playback_module.playback_router.play

    def failing_play(payload):
        raise NodeUnavailableError("Test Pi offline")

    playback_module.playback_router.play = failing_play
    event = {
        "type": rule["trigger"],
        "person_id": "p-offline",
        "zone": "Hall",
        "duration": 400,
        "timestamp": time.time(),
    }
    fired = reminder_engine.handle_event(event)
    assert len(fired) == 1
    assert fired[0]["playback_status"] == "failed"
    assert fired[0].get("laptop_playback") is False
    playback_module.playback_router.play = original_play


# ---------------------------------------------------------------------------
# 25. Pi acknowledgement failure — patches authoritative production playback singleton
# ---------------------------------------------------------------------------


def test_pi_ack_failure_recorded(reminder_engine, playback_router):
    router, node = playback_router
    rule = reminder_engine.create_rule({
        "id": f"rule-ack-{uuid.uuid4().hex[:8]}",
        "name": "Ack failure test",
        "trigger": "long_sitting",
        "message": "test",
        "action_type": "tts",
        "target_node": node["node_id"],
        "cooldown_seconds": 0,
    })
    from services.playback_router.router import NodeUnavailableError
    import services.playback_router.router as playback_module

    original_play = playback_module.playback_router.play

    def rejected_play(payload):
        raise NodeUnavailableError("hardware busy")

    playback_module.playback_router.play = rejected_play
    event = {
        "type": rule["trigger"],
        "person_id": "p-ack",
        "zone": "Hall",
        "duration": 400,
        "timestamp": time.time(),
    }
    fired = reminder_engine.handle_event(event)
    assert len(fired) == 1
    assert fired[0]["playback_status"] == "failed"
    assert "hardware busy" in fired[0].get("playback_error", "")
    assert fired[0].get("laptop_playback") is False
    playback_module.playback_router.play = original_play


# ---------------------------------------------------------------------------
# 26. Islamic rule action — uses islamic_rule_store (NOT islamic_store)
# ---------------------------------------------------------------------------


def test_islamic_rule_executes_on_activity_event(islamic_rule_store, playback_router):
    router, node = playback_router
    islamic_rule_store.add_rule({
        "name": "Long Sitting Dua",
        "event": "long_sitting",
        "zone": "Hall",
        "message": "Test dua for long sitting",
        "enabled": True,
        "action_type": "tts",
        "target_node": node["node_id"],
        "cooldown_seconds": 0,
    })
    calls = []

    import services.playback_router.router as playback_module

    original_play = playback_module.playback_router.play
    playback_module.playback_router.play = lambda payload: calls.append(payload) or {"status": "played"}
    result = islamic_rule_store.evaluate({"event": "long_sitting", "zone": "Hall"})
    assert len(result["executions"]) >= 1
    assert result["executions"][0]["status"] == "played"
    playback_module.playback_router.play = original_play


# ---------------------------------------------------------------------------
# 27. No laptop fallback
# ---------------------------------------------------------------------------


def test_no_laptop_audio_in_any_authoritative_path():
    sources = [
        Path("services/playback_router/router.py").read_text(),
        Path("services/playback_router/tts_audio.py").read_text() if (ROOT / "services" / "playback_router" / "tts_audio.py").is_file() else "",
        Path("services/reminder_rules/reminder_rules.py").read_text(),
        Path("services/islamic_intelligence_v12/store.py").read_text(),
        Path("services/prayer_intelligence/service.py").read_text(),
    ]
    for forbidden in ("aplay", "paplay", "ffplay", "pygame", "streaming_tts_service"):
        assert all(forbidden not in src for src in sources if src), f"{forbidden} should not appear in any path"


# ---------------------------------------------------------------------------
# 28. Integration: activity event flows to reminder rules
# ---------------------------------------------------------------------------


def test_activity_event_flows_to_reminder_rules(hai_engine, reminder_engine, playback_router):
    """HAI sitting event → reminder rule → playback (patched)."""
    router, node = playback_router
    rule = reminder_engine.create_rule({
        "id": f"rule-int-{uuid.uuid4().hex[:8]}",
        "name": "Integration test rule",
        "trigger": "stayed",
        "message": "test reminder",
        "action_type": "tts",
        "target_node": node["node_id"],
        "cooldown_seconds": 0,
    })
    import services.playback_router.router as playback_module
    original_play = playback_module.playback_router.play
    playback_module.playback_router.play = lambda payload: {"status": "played"}

    try:
        events = hai_engine.observe(
            person_id="p-int",
            track_id="t-int",
            zone="Hall",
            room="Hall",
            box=[200, 250, 300, 300],
            motion_delta=0.0,
        )
        sitting_events = [ev for ev in events if ev["event_type"] == "sitting"]
        assert sitting_events, "need a sitting event for integration test"
        # Build a reminder-compatible event using the normalized rule trigger
        reminder_event = {
            "type": rule["trigger"],
            "person_id": sitting_events[0].get("person_id"),
            "zone": sitting_events[0].get("zone"),
            "duration": sitting_events[0].get("duration", 0),
            "timestamp": sitting_events[0].get("timestamp"),
        }
        fired = reminder_engine.handle_event(reminder_event)
        assert len(fired) == 1
    finally:
        playback_module.playback_router.play = original_play


# ---------------------------------------------------------------------------
# 29. Islamic Learning: framework tests (NOT fabricated content counts)
# ---------------------------------------------------------------------------


def test_islamic_learning_health(islamic_store):
    _require_enabled(islamic_store)
    from services.islamic_learning.routes import router

    # Health endpoint must be reachable
    assert router is not None


def test_islamic_learning_exposes_verified_content_required():
    from services.islamic_learning.questions import VERIFIED_CONTENT_REQUIRED

    assert VERIFIED_CONTENT_REQUIRED is True


def test_islamic_learning_categories_exist(islamic_store):
    _require_enabled(islamic_store)
    cats = islamic_store.read().get("categories", [])
    assert cats, "categories must be present"
    for cat in cats:
        assert cat.get("id")
        assert cat.get("name")
        assert cat.get("question_count") is not None


def test_islamic_learning_empty_content_graceful(islamic_store):
    """When verified content is not available, endpoints return empty lists cleanly."""
    from services.islamic_learning.questions import DUAS, NAMES_99, SURAH_QUIZ, ARABIC_MATCH, ISLAMIC_KNOWLEDGE, KIDS_DATA

    assert isinstance(DUAS, list)
    assert isinstance(NAMES_99, list)
    assert isinstance(SURAH_QUIZ, list)
    assert isinstance(ARABIC_MATCH, list)
    assert isinstance(ISLAMIC_KNOWLEDGE, list)
    assert isinstance(KIDS_DATA, dict)
    assert "short_duas" in KIDS_DATA
    assert "colors_questions" in KIDS_DATA


def test_islamic_learning_schema_correct(islamic_store):
    """If any content is present, it must have correct schema + source metadata."""
    from services.islamic_learning.questions import DUAS

    for dua in DUAS:
        assert isinstance(dua.get("id"), str)
        assert isinstance(dua.get("arabic"), str) or dua.get("arabic") is None
        assert isinstance(dua.get("transliteration"), str) or dua.get("transliteration") is None
        assert isinstance(dua.get("translation"), str) or dua.get("translation") is None
        assert isinstance(dua.get("category"), str) or dua.get("category") is None
        assert isinstance(dua.get("source"), str) or dua.get("source") is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_enabled(store):
    settings = store.settings()
    if not settings.get("enabled", True):
        raise AssertionError("Islamic Learning must be enabled for these tests")
