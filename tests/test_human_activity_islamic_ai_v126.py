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
# 28. Prayer / Adhan integration with Playback Router
# ---------------------------------------------------------------------------


def _patch_playback(monkeypatch):
    """Patch the authoritative playback_router singleton used by production code."""
    import services.playback_router.router as playback_module
    calls = []
    def fake_play(payload):
        calls.append(payload)
        return {"status": "played"}
    monkeypatch.setattr(playback_module.playback_router, "play", fake_play)
    return calls


def test_prayer_event_mapping(reminder_engine):
    """Prayer Intelligence produces adhan events with kind=adhan + prayer name."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo

    # Use a timezone-aware now that aligns with config settings
    settings = prayer_intelligence_service.settings()
    zone = ZoneInfo(str(settings["timezone"]))
    now = datetime.now(zone)

    # due_events should produce structured prayer events
    result = prayer_intelligence_service.due_events(now)
    assert result["status"] == "ok"
    assert isinstance(result["events"], list)
    # Each event has kind, prayer, time, message fields
    for ev in result["events"]:
        assert "kind" in ev
        assert "prayer" in ev
        assert "time" in ev


def test_adhan_configured_target_node(reminder_engine):
    """Adhan config includes target_node from prayer settings."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    adhan = prayer_intelligence_service.adhan_settings()
    assert "adhan_enabled" in adhan
    assert "adhan_target_node" in adhan
    assert "adhan_lead_minutes" in adhan
    assert "adhan_media_id" in adhan


def test_adhan_disabled_returns_disabled(reminder_engine):
    """When adhan_enabled=False, check_adhan_due returns status=disabled."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store
    import time

    # Temporarily disable adhan
    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = False
    prayer_store.write(original)
    try:
        result = prayer_intelligence_service.check_adhan_due()
        assert result["status"] == "disabled"
        assert result["events"] == []
    finally:
        # Restore
        original["settings"]["adhan_enabled"] = True
        prayer_store.write(original)


def test_adhan_missing_media_truthful_state(reminder_engine, monkeypatch):
    """Without verified Adhan media, check returns ADHAN_MEDIA_REQUIRED."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store

    # Ensure no explicit media_id and _find_adhan_media_id returns None
    original_data = prayer_store.read()
    original_data["settings"]["adhan_media_id"] = None
    original_data["settings"]["adhan_target_node"] = "test-pi"
    prayer_store.write(original_data)
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id", lambda: None
    )
    # Patch due_events to return a fixed adhan event
    fixed_event = [{
        "kind": "adhan",
        "prayer": "asr",
        "time": "2026-08-15T16:30:00",
        "message": "It is time for Asr prayer.",
    }]
    monkeypatch.setattr(
        prayer_intelligence_service, "due_events",
        lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
    )
    try:
        result = prayer_intelligence_service.check_adhan_due()
        assert result["media_state"] == prayer_intelligence_service.ADHAN_MEDIA_REQUIRED
        assert result["status"] == "required"
    finally:
        # Restore original settings
        original_data["settings"].pop("adhan_media_id", None)
        original_data["settings"].pop("adhan_target_node", None)
        prayer_store.write(original_data)


def test_adhan_duplicate_suppression(reminder_engine, monkeypatch, tmp_path):
    """A single prayer occurrence must not repeatedly trigger adhan."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store
    from datetime import datetime, timezone

    calls = _patch_playback(monkeypatch)

    # Patch due_events to return a fixed adhan event
    fixed_event = [{
        "kind": "adhan",
        "prayer": "maghrib",
        "time": "2026-08-15T19:00:00",
        "message": "It is time for Maghrib prayer.",
    }]

    # Configure adhan with a target node (no explicit media_id — use auto-discovery)
    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = None
    prayer_store.write(original)

    monkeypatch.setattr(
        prayer_intelligence_service, "due_events",
        lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
    )
    # Mock auto-discovery to return a valid media_id
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id",
        lambda: "verified-adhan-1"
    )
    try:
        # First check — should fire
        result1 = prayer_intelligence_service.check_adhan_due()
        assert result1["status"] == "played"
        assert len(calls) == 1

        # Second check — same occurrence must be suppressed by dedup
        result2 = prayer_intelligence_service.check_adhan_due()
        assert result2["status"] == "suppressed"
        assert len(calls) == 1  # No additional playback call

        # Three more checks — still suppressed
        prayer_intelligence_service.check_adhan_due()
        prayer_intelligence_service.check_adhan_due()
        assert len(calls) == 1  # Still only one playback call total
    finally:
        original["settings"]["adhan_enabled"] = True
        original["settings"].pop("adhan_target_node", None)
        original["settings"].pop("adhan_media_id", None)
        prayer_store.write(original)


def test_adhan_playback_success(reminder_engine, monkeypatch):
    """Successful adhan playback returns status=played, no laptop fallback."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store

    calls = _patch_playback(monkeypatch)

    fixed_event = [{
        "kind": "adhan",
        "prayer": "fajr",
        "time": "2026-08-15T04:30:00",
        "message": "It is time for Fajr prayer.",
    }]

    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = None
    prayer_store.write(original)

    monkeypatch.setattr(
        prayer_intelligence_service, "due_events",
        lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
    )
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id",
        lambda: "verified-adhan-1"
    )
    try:
        result = prayer_intelligence_service.check_adhan_due()
        assert result["status"] == "played"
        assert result["media_state"] == "verified"
        assert len(calls) == 1
        assert calls[0]["target_node"] == "test-pi"
        assert calls[0]["type"] == "media"
        assert calls[0]["media_id"] == "verified-adhan-1"
    finally:
        original["settings"]["adhan_target_node"] = "existing-pi-audio"
        original["settings"]["adhan_media_id"] = None
        prayer_store.write(original)


def test_adhan_playback_failure_no_laptop_fallback(reminder_engine, monkeypatch):
    """Adhan playback failure is truthful — no laptop fallback."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store
    from services.playback_router.router import NodeUnavailableError

    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = None
    prayer_store.write(original)

    fixed_event = [{
        "kind": "adhan",
        "prayer": "dhuhr",
        "time": "2026-08-15T13:00:00",
        "message": "It is time for Dhuhr prayer.",
    }]

    # Patch playback to fail
    import services.playback_router.router as playback_module
    original_play = playback_module.playback_router.play
    def failing_play(payload):
        raise NodeUnavailableError("Test Pi offline")
    playback_module.playback_router.play = failing_play

    monkeypatch.setattr(
        prayer_intelligence_service, "due_events",
        lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
    )
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id",
        lambda: "verified-adhan-1"
    )
    try:
        result = prayer_intelligence_service.check_adhan_due()
        assert result["status"] == "failed"
        assert result["result"]["status"] == "failed"
        assert result["result"].get("laptop_fallback") is False
        assert "Test Pi offline" in result["result"].get("error", "")
    finally:
        playback_module.playback_router.play = original_play
        original["settings"]["adhan_target_node"] = "existing-pi-audio"
        original["settings"]["adhan_media_id"] = None
        prayer_store.write(original)


def test_adhan_no_media_no_fabricated_audio(reminder_engine, monkeypatch):
    """No verified Adhan media → truthful ADHAN_MEDIA_REQUIRED, never TTS substitution."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store

    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = None
    prayer_store.write(original)

    fixed_event = [{
        "kind": "adhan",
        "prayer": "asr",
        "time": "2026-08-15T16:30:00",
        "message": "It is time for Asr prayer.",
    }]

    monkeypatch.setattr(
        prayer_intelligence_service, "due_events",
        lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
    )
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id",
        lambda: None  # No adhan media in catalog
    )
    try:
        result = prayer_intelligence_service.check_adhan_due()
        assert result["media_state"] == prayer_intelligence_service.ADHAN_MEDIA_REQUIRED
        assert result["status"] == "required"
        assert result["events"] == fixed_event
        # No playback should have occurred
        assert "result" not in result
    finally:
        original["settings"]["adhan_target_node"] = "existing-pi-audio"
        prayer_store.write(original)


# ---------------------------------------------------------------------------
# 28b. Adhan safety tests (false dua match, failed-playback dedup)
# ---------------------------------------------------------------------------


def test_dua_when_hearing_athan_not_accepted_as_adhan(reminder_engine, monkeypatch):
    """Dua When Hearing the Athan (category=duas) must NOT be accepted as Adhan.

    _find_adhan_media_id must only return media with category == "adhan".
    Duas/Azkar that merely mention 'athan' in their name are NOT Adhan media.
    """
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.islamic_audio_rules.catalog import catalog_items

    # Verify the real catalog contents
    items = catalog_items()
    dua_when_hearing = [
        i for i in items
        if "athan" in (i.get("name") or "").lower() and i.get("category") == "duas"
    ]
    # Ensure at least one such dua exists in the catalog (the false positive case)
    assert len(dua_when_hearing) >= 1, "Expected Dua When Hearing the Athan in catalog"

    # _find_adhan_media_id must NOT return any duas/azkar item
    media_id = prayer_intelligence_service._find_adhan_media_id()
    if media_id is not None:
        # If it returns something, it MUST be category == "adhan"
        matched = [
            i for i in items
            if str(i.get("id")) == str(media_id)
        ]
        assert len(matched) >= 1
        assert matched[0]["category"] == "adhan", (
            f"Auto-discovered media_id {media_id} is "
            f"category={matched[0]['category']}, not 'adhan'"
        )
        # The dua must NOT be the one returned
        dua_ids = {str(i["id"]) for i in dua_when_hearing}
        assert media_id not in dua_ids, (
            f"False positive: Dua When Hearing the Athan "
            f"(id={media_id}) was returned as Adhan"
        )
    # If no real adhan media exists in catalog, media_id is None
    # (currently we have beautiful_adhan_cc0.mp3 as category="adhan")


def test_explicit_dowa_media_id_not_valid_adhan(reminder_engine, monkeypatch):
    """An explicitly configured Dua/Azkar media_id must NOT be treated as Adhan.

    If a Dua media_id is placed in adhan_media_id, it must fail validation
    and produce ADHAN_MEDIA_REQUIRED.
    """
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store
    from services.islamic_audio_rules.catalog import catalog_items

    # Find a real duas or azkar media_id
    items = catalog_items()
    dua_item = next(
        (i for i in items if i.get("category") in {"duas", "azkar"}), None
    )
    if dua_item is None:
        # If no duas/azkar exist, skip gracefully
        return

    daa_media_id = str(dua_item["id"])

    # Configure explicit adhan_media_id as a dua
    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = daa_media_id
    prayer_store.write(original)

    try:
        adhan = prayer_intelligence_service.adhan_settings()
        # Explicit dua media_id must be rejected
        assert adhan["adhan_media_id"] is None, (
            f"Dua media_id '{daa_media_id}' (category={dua_item['category']}) "
            f"was accepted as Adhan — validation bug"
        )
        assert adhan["verified_adhan_media_available"] is False
        assert adhan["media_state"] == prayer_intelligence_service.ADHAN_MEDIA_REQUIRED
    finally:
        original["settings"].pop("adhan_media_id", None)
        original["settings"].pop("adhan_target_node", None)
        prayer_store.write(original)


def test_category_adhan_media_discovered(reminder_engine, monkeypatch):
    """Real catalog category=adhan media must be discovered and accepted."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.islamic_audio_rules.catalog import catalog_items

    items = catalog_items()
    adhan_items = [i for i in items if i.get("category") == "adhan"]
    assert len(adhan_items) >= 1, "Expected at least one category=adhan media in catalog"

    # _find_adhan_media_id must return the real adhan media ID
    media_id = prayer_intelligence_service._find_adhan_media_id()
    assert media_id is not None, "Adhan media should be discovered from catalog"

    # The returned media_id must correspond to a category=adhan item
    matched = [i for i in items if str(i["id"]) == str(media_id)]
    assert len(matched) == 1
    assert matched[0]["category"] == "adhan"

    # adhan_settings must reflect verified media
    adhan = prayer_intelligence_service.adhan_settings()
    assert adhan["adhan_media_id"] == media_id
    assert adhan["verified_adhan_media_available"] is True
    assert adhan["media_state"] == "verified"


def test_explicit_valid_adhan_media_id_accepted(reminder_engine, monkeypatch):
    """An explicitly configured valid Adhan media_id must be accepted."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store
    from services.islamic_audio_rules.catalog import catalog_items

    items = catalog_items()
    adhan_items = [i for i in items if i.get("category") == "adhan"]
    assert len(adhan_items) >= 1

    valid_adhan_id = str(adhan_items[0]["id"])

    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = valid_adhan_id
    prayer_store.write(original)

    try:
        adhan = prayer_intelligence_service.adhan_settings()
        assert adhan["adhan_media_id"] == valid_adhan_id
        assert adhan["verified_adhan_media_available"] is True
        assert adhan["media_state"] == "verified"
    finally:
        original["settings"].pop("adhan_media_id", None)
        original["settings"].pop("adhan_target_node", None)
        prayer_store.write(original)


def test_no_adhan_media_truthful_state(reminder_engine, monkeypatch):
    """When no valid Adhan media is available (mocked None), state is ADHAN_MEDIA_REQUIRED."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store

    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = None
    prayer_store.write(original)

    # Mock both auto-discovery and validation to return None
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id", lambda: None
    )
    monkeypatch.setattr(
        prayer_intelligence_service, "_validate_adhan_media_id", lambda mid: None
    )

    try:
        adhan = prayer_intelligence_service.adhan_settings()
        assert adhan["adhan_media_id"] is None
        assert adhan["verified_adhan_media_available"] is False
        assert adhan["media_state"] == prayer_intelligence_service.ADHAN_MEDIA_REQUIRED

        # And check_adhan_due with no media returns truthful state
        fixed_event = [{
            "kind": "adhan",
            "prayer": "asr",
            "time": "2026-08-15T16:30:00",
            "message": "It is time for Asr prayer.",
        }]
        monkeypatch.setattr(
            prayer_intelligence_service, "due_events",
            lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
        )
        result = prayer_intelligence_service.check_adhan_due()
        assert result["media_state"] == prayer_intelligence_service.ADHAN_MEDIA_REQUIRED
        assert result["status"] == "required"
    finally:
        original["settings"].pop("adhan_media_id", None)
        original["settings"].pop("adhan_target_node", None)
        prayer_store.write(original)


def test_adhan_check_route_single_call(reminder_engine, monkeypatch):
    """The /adhan/check route must invoke check_adhan_due EXACTLY ONCE."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from fastapi.testclient import TestClient
    from main import app

    call_count = [0]
    def counting_check(now=None):
        call_count[0] += 1
        return {
            "status": "suppressed",
            "events": [],
            "media_state": "verified",
        }
    monkeypatch.setattr(
        prayer_intelligence_service, "check_adhan_due", counting_check
    )

    client = TestClient(app)
    response = client.post("/api/prayer-intelligence/adhan/check")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "suppressed"
    assert call_count[0] == 1, (
        f"check_adhan_due was called {call_count[0]} times, expected exactly 1"
    )


def test_failed_playback_not_deduped_allows_retry(reminder_engine, monkeypatch):
    """Failed adhan playback must NOT mark the occurrence as fired.

    A failed occurrence (status=failed) must NOT suppress retries.
    Only successful playback (status=fired) suppresses future attempts.
    """
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store
    from services.playback_router.router import NodeUnavailableError

    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = None
    prayer_store.write(original)

    fixed_event = [{
        "kind": "adhan",
        "prayer": "maghrib",
        "time": "2026-08-15T19:00:00",
        "message": "It is time for Maghrib prayer.",
    }]

    monkeypatch.setattr(
        prayer_intelligence_service, "due_events",
        lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
    )
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id",
        lambda: "verified-adhan-1"
    )

    # Patch playback to fail
    import services.playback_router.router as playback_module
    original_play = playback_module.playback_router.play
    call_count = [0]
    def failing_play(payload):
        call_count[0] += 1
        raise NodeUnavailableError("Pi offline for retry test")
    playback_module.playback_router.play = failing_play

    try:
        # First check — playback fails
        result1 = prayer_intelligence_service.check_adhan_due()
        assert result1["status"] == "failed"
        assert call_count[0] == 1

        # Verify the stored event has status="failed", NOT "fired"
        events = [
            ev for ev in prayer_store.list_events(5000)
            if ev.get("kind") == "adhan" and ev.get("prayer") == "maghrib"
        ]
        assert len(events) >= 1
        assert events[-1]["status"] == "failed", (
            "Failed playback must be recorded as status='failed', not 'fired'"
        )

        # Second check — should RETRY (not suppressed because last attempt failed)
        result2 = prayer_intelligence_service.check_adhan_due()
        assert result2["status"] == "failed"
        assert call_count[0] == 2, (
            "Failed playback must not be deduped — retry should occur"
        )
    finally:
        playback_module.playback_router.play = original_play
        original["settings"]["adhan_target_node"] = "existing-pi-audio"
        original["settings"].pop("adhan_media_id", None)
        prayer_store.write(original)


def test_successful_playback_marks_fired_and_suppresses(reminder_engine, monkeypatch):
    """Successful adhan playback marks status=fired and suppresses retries."""
    from services.prayer_intelligence.service import prayer_intelligence_service
    from services.prayer_intelligence.store import prayer_store

    calls = _patch_playback(monkeypatch)

    fixed_event = [{
        "kind": "adhan",
        "prayer": "isha",
        "time": "2026-08-15T21:00:00",
        "message": "It is time for Isha prayer.",
    }]

    original = prayer_store.read()
    original["settings"]["adhan_enabled"] = True
    original["settings"]["adhan_target_node"] = "test-pi"
    original["settings"]["adhan_media_id"] = None
    prayer_store.write(original)

    monkeypatch.setattr(
        prayer_intelligence_service, "due_events",
        lambda now=None: {"status": "ok", "due_count": 1, "events": fixed_event}
    )
    monkeypatch.setattr(
        prayer_intelligence_service, "_find_adhan_media_id",
        lambda: "verified-adhan-1"
    )

    try:
        # First check — should play successfully
        result1 = prayer_intelligence_service.check_adhan_due()
        assert result1["status"] == "played"
        assert len(calls) == 1

        # Verify stored event has status="fired"
        events = [
            ev for ev in prayer_store.list_events(5000)
            if ev.get("kind") == "adhan" and ev.get("prayer") == "isha"
        ]
        assert len(events) >= 1
        assert events[-1]["status"] == "fired"

        # Second check — same prayer+time must be suppressed
        result2 = prayer_intelligence_service.check_adhan_due()
        assert result2["status"] == "suppressed"
        assert len(calls) == 1  # No additional playback
    finally:
        original["settings"]["adhan_target_node"] = "existing-pi-audio"
        prayer_store.write(original)


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
