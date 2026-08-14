from __future__ import annotations

import json
from pathlib import Path

import pytest

import services.playback_router.router as playback_module
from services.playback_router.router import NodeUnavailableError, PlaybackRouter


def configured_router(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[PlaybackRouter, dict]:
    monkeypatch.setattr(playback_module, "STORE", tmp_path / "nodes.json")
    monkeypatch.setattr(playback_module, "LEGACY_CONFIG", tmp_path / "missing-legacy.json")
    router = PlaybackRouter()
    node = router.create_node({
        "name": "Hall Pi",
        "room": "Hall",
        "url": "http://192.0.2.20:8010",
        "token": "trusted-test-token",
        "capabilities": {"microphone": True, "speaker": True, "playback": True},
    })
    return router, node


def test_playback_requires_explicit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, _ = configured_router(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="target Raspberry Pi"):
        router.play({"type": "tts", "content": "Take your keys"})


def test_tts_success_requires_node_ack_and_never_uses_laptop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, node = configured_router(tmp_path, monkeypatch)
    calls = []

    def accepted(target, path, **kwargs):
        calls.append((target["node_id"], path, kwargs))
        return {"status": "played", "engine": "node-tts"}

    monkeypatch.setattr(router, "_request", accepted)
    result = router.play({"target_node": node["node_id"], "type": "tts", "content": "Take your keys", "volume": 70})
    assert result["status"] == "played"
    assert result["laptop_playback"] is False
    assert calls[0][1] == "/tts"
    assert calls[0][2]["payload"]["volume"] == 70


def test_offline_node_is_truthful_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, node = configured_router(tmp_path, monkeypatch)

    def offline(*args, **kwargs):
        raise NodeUnavailableError("Target speaker unavailable")

    monkeypatch.setattr(router, "_request", offline)
    with pytest.raises(NodeUnavailableError, match="unavailable"):
        router.play({"target_node": node["node_id"], "type": "tts", "content": "Test"})


def test_listen_session_is_explicit_and_closes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, node = configured_router(tmp_path, monkeypatch)

    def node_api(target, path, **kwargs):
        if path == "/listen/start":
            return {"status": "listening", "session_id": "node-session"}
        if path.endswith("/chunk"):
            return {"status": "captured", "format": "wav", "audio_base64": "UklGRg=="}
        if path.endswith("/stop"):
            return {"status": "stopped", "remote_listening_active": False}
        raise AssertionError(path)

    monkeypatch.setattr(router, "_request", node_api)
    started = router.start_listen(node["node_id"])
    assert started["remote_listening_active"] is True
    assert router.listen_chunk(started["session_id"])["status"] == "captured"
    stopped = router.stop_listen(started["session_id"])
    assert stopped["remote_listening_active"] is False
    assert started["session_id"] not in router._listen_sessions


def test_node_store_never_returns_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, node = configured_router(tmp_path, monkeypatch)
    assert node["trusted"] is True
    assert node["token"] == ""
    persisted = json.loads((tmp_path / "nodes.json").read_text())
    assert persisted["nodes"][0]["token"] == "trusted-test-token"


def test_no_server_audio_fallback_in_authoritative_paths() -> None:
    sources = [
        Path("services/playback_router/router.py").read_text(),
        Path("services/smart_automation/action_executor.py").read_text(),
        Path("services/reminder_rules/reminder_rules.py").read_text(),
        Path("services/islamic_reminders/service.py").read_text(),
        Path("services/prayer_intelligence/service.py").read_text(),
        Path("services/personalized_halo/service.py").read_text(),
        Path("services/islamic_audio_control/service.py").read_text(),
        Path("services/media_library/media_manager.py").read_text(),
    ]
    for forbidden in ("aplay", "paplay", "ffplay", "pygame", "streaming_tts_service"):
        assert all(forbidden not in source for source in sources)


def test_islamic_rule_uses_production_router_and_cooldown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from services.islamic_intelligence_v12.store import Store

    store = Store()
    store.path = tmp_path / "islamic-rules.json"
    store.write({
        "version": "12.0.0",
        "settings": {},
        "events": [],
        "rules": [{
            "id": "kitchen-dua",
            "name": "Kitchen Dua",
            "event": "person_entered",
            "zone": "Kitchen",
            "message": "Bismillah",
            "enabled": True,
            "action_type": "tts",
            "target_node": "kitchen-pi",
            "cooldown_seconds": 300,
        }],
    })
    calls = []
    monkeypatch.setattr(playback_module.playback_router, "play", lambda payload: calls.append(payload) or {"status": "played"})

    first = store.evaluate({"event": "person_entered", "zone": "Kitchen"})
    second = store.evaluate({"event": "person_entered", "zone": "Kitchen"})
    assert first["executions"][0]["status"] == "played"
    assert calls[0]["target_node"] == "kitchen-pi"
    assert second["executions"] == []
