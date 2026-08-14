from __future__ import annotations

import importlib.util
import json
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import services.playback_router.router as playback_module
from services.playback_router.router import NodeUnavailableError, PlaybackRouter


ROOT = Path(__file__).resolve().parents[1]
NODE_SOURCE = ROOT / "tools" / "noorbrain_pi_audio_node.py"


def load_node_module():
    spec = importlib.util.spec_from_file_location("noorbrain_pi_audio_node_contract_test", NODE_SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def node_client(monkeypatch: pytest.MonkeyPatch):
    module = load_node_module()
    monkeypatch.setattr(module, "NODE_TOKEN", "correct-shared-node-token-for-tests")
    monkeypatch.setattr(module, "hardware_available", lambda executable, device: True)
    monkeypatch.setattr(module, "play_audio", lambda payload, source_type: {"status": "played", "type": source_type})
    monkeypatch.setattr(module, "capture_audio", lambda seconds: {
        "status": "captured", "format": "wav", "seconds": int(seconds), "audio_base64": "UklGRg=="
    })
    return module, TestClient(module.app)


def auth_header() -> dict[str, str]:
    return {"X-NoorBrain-Node-Token": "correct-shared-node-token-for-tests"}


@pytest.mark.parametrize("headers", [{}, {"X-NoorBrain-Node-Token": "wrong-token"}])
def test_play_rejects_missing_and_wrong_token(node_client, headers: dict[str, str]) -> None:
    _, client = node_client
    response = client.post("/play", json={"audio_base64": "UklGRg==", "format": "wav"}, headers=headers)
    assert response.status_code == 401


def test_correct_token_accepts_play_and_talk(node_client) -> None:
    _, client = node_client
    for path in ("/play", "/talk"):
        response = client.post(path, json={"audio_base64": "UklGRg==", "format": "wav"}, headers=auth_header())
        assert response.status_code == 200
        assert response.json()["status"] == "played"
    assert client.post("/stop").status_code == 401
    assert client.post("/stop", headers=auth_header()).status_code == 200


def test_record_and_listen_require_authentication(node_client) -> None:
    _, client = node_client
    assert client.post("/record", json={"seconds": 1}).status_code == 401
    assert client.post("/record", json={"seconds": 1}, headers={"X-NoorBrain-Node-Token": "wrong"}).status_code == 401
    assert client.post("/listen/start").status_code == 401

    recorded = client.post("/record", json={"seconds": 1}, headers=auth_header())
    assert recorded.status_code == 200
    started = client.post("/listen/start", headers=auth_header())
    assert started.status_code == 200
    session = started.json()["session_id"]
    chunk = client.post(f"/listen/{session}/chunk", json={"seconds": 1}, headers=auth_header())
    assert chunk.status_code == 200
    stopped = client.post(f"/listen/{session}/stop", headers=auth_header())
    assert stopped.json()["remote_listening_active"] is False


def test_health_reports_authoritative_hardware_contract(node_client) -> None:
    _, client = node_client
    health = client.get("/health").json()
    assert health["service"] == "noorbrain_pi_audio"
    assert health["version"] == "2.1.0"
    assert health["speaker_available"] is True
    assert health["microphone_available"] is True
    assert health["playback_device"] == "plughw:CARD=Headphones,DEV=0"
    assert health["capture_device"] == "plughw:CARD=Device,DEV=0"
    assert health["remote_listening_active"] is False


def configured_router(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[PlaybackRouter, dict]:
    monkeypatch.setattr(playback_module, "STORE", tmp_path / "nodes.json")
    monkeypatch.setattr(playback_module, "LEGACY_CONFIG", tmp_path / "missing.json")
    router = PlaybackRouter()
    public = router.create_node({
        "node_id": "existing-pi-audio",
        "name": "Physical Pi",
        "room": "Hall",
        "url": "http://192.168.2.29:8010",
        "token": "server-shared-token",
        "capabilities": {"microphone": True, "speaker": True, "playback": True},
    })
    return router, public


def test_server_sends_shared_token_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, _ = configured_router(tmp_path, monkeypatch)
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"status":"played"}'

    def urlopen(request: urllib.request.Request, timeout: int):
        seen["token"] = request.get_header("X-noorbrain-node-token")
        seen["url"] = request.full_url
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    node = router.get_node("existing-pi-audio")
    assert router._request(node, "/play", method="POST", payload={"audio_base64": "UklGRg=="})["status"] == "played"
    assert seen == {"token": "server-shared-token", "url": "http://192.168.2.29:8010/play"}


def test_existing_node_can_gain_token_without_recreation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(playback_module, "STORE", tmp_path / "nodes.json")
    monkeypatch.setattr(playback_module, "LEGACY_CONFIG", tmp_path / "missing.json")
    router = PlaybackRouter()
    created = router.create_node({
        "node_id": "existing-pi-audio",
        "name": "Existing Raspberry Pi",
        "room": "Hall",
        "url": "http://192.168.2.29:8010",
        "capabilities": {"microphone": True, "speaker": True, "playback": True},
    })
    assert created["trusted"] is False
    updated = router.update_node("existing-pi-audio", {"token": "new-shared-token-with-enough-entropy"})
    assert updated["node_id"] == "existing-pi-audio"
    assert updated["name"] == "Existing Raspberry Pi"
    assert updated["url"] == "http://192.168.2.29:8010"
    assert updated["trusted"] is True
    assert "token" not in updated


def test_tts_media_dua_and_azkar_all_send_audio_to_pi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, node = configured_router(tmp_path, monkeypatch)
    media_path = tmp_path / "dua.mp3"
    media_path.write_bytes(b"ID3-test-audio")
    monkeypatch.setattr(playback_module.media_library, "get_item", lambda media_id: {"id": media_id, "name": "Dua"})
    monkeypatch.setattr(playback_module.media_library, "get_file_path", lambda media_id: media_path)
    monkeypatch.setattr(playback_module, "synthesize_tts_audio", lambda text: (b"RIFF" + b"\0" * 48, "wav", {"engine": "test"}))
    calls = []
    monkeypatch.setattr(router, "_request", lambda target, path, **kwargs: calls.append((path, kwargs["payload"])) or {"status": "played"})

    requests = [
        {"type": "tts", "content": "Assalamu Alaikum"},
        {"type": "media", "media_id": "dua-media"},
        {"type": "dua", "media_id": "dua-media"},
        {"type": "azkar", "content": "SubhanAllah"},
    ]
    for request in requests:
        result = router.play({"target_node": node["node_id"], **request})
        assert result["status"] == "played"
        assert result["laptop_playback"] is False
    assert all(path == "/play" for path, _ in calls)
    assert all(payload.get("audio_base64") for _, payload in calls)
    assert all("text" not in payload for _, payload in calls)


def test_pi_rejection_is_truthful_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    router, node = configured_router(tmp_path, monkeypatch)
    monkeypatch.setattr(playback_module, "synthesize_tts_audio", lambda text: (b"RIFF" + b"\0" * 48, "wav", {"engine": "test"}))
    monkeypatch.setattr(router, "_request", lambda *args, **kwargs: {"status": "rejected", "detail": "hardware busy"})
    with pytest.raises(NodeUnavailableError, match="hardware busy"):
        router.play({"target_node": node["node_id"], "type": "tts", "content": "Test"})


def test_deployment_uses_pi_venv_systemd_and_no_committed_secret() -> None:
    deployer = (ROOT / "tools" / "deploy_noorbrain_pi_audio_node.sh").read_text()
    service = (ROOT / "deploy" / "pi-audio" / "noorbrain-pi-audio.service.in").read_text()
    node = NODE_SOURCE.read_text()
    legacy_installer = (ROOT / "installer" / "dual_audio_v15" / "install.py").read_text()
    assert "Projects/NoorCameraNode" in deployer
    assert "Projects/NoorCameraNode/venv/bin/python" in service
    assert "systemctl enable --now noorbrain-pi-audio.service" in deployer
    assert "Restart=on-failure" in service
    assert 'NOORBRAIN_NODE_TOKEN", ""' in node
    assert "X-NoorBrain-Node-Token" in node
    assert "plughw:CARD=Headphones,DEV=0" in node
    assert "plughw:CARD=Device,DEV=0" in node
    assert "PI_NODE=" not in legacy_installer
    assert "deploy_noorbrain_pi_audio_node.sh" in legacy_installer
