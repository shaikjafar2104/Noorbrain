from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from services.automation.manager import DeviceManager
from services.automation.storage import DeviceStorage
from services.smart_automation.action_executor import AutomationActionExecutor
from services.unified_device_runtime.executor import PhysicalDeviceExecutor
from services.unified_device_runtime.service import UnifiedDeviceRuntime


ROOT = Path(__file__).resolve().parents[1]


def test_checked_in_runtime_is_valid_zero_device_state() -> None:
    payload = json.loads((ROOT / "data/smart_home_runtime.json").read_text())
    assert payload["rooms"] == []
    assert payload["devices"] == []
    assert payload["scenes"] == []


def test_offline_and_logical_devices_cannot_report_state_changes(tmp_path: Path) -> None:
    manager = DeviceManager(DeviceStorage(tmp_path / "devices.json"))
    offline = manager.create_device({
        "name": "Offline test light",
        "device_type": "light",
        "room": "Test",
        "state": "off",
        "online": False,
    })

    with pytest.raises(RuntimeError, match="offline"):
        manager.set_state(offline.id, "on")
    assert manager.get_device(offline.id).state == "off"

    logical = manager.create_device({
        "name": "Logical test light",
        "device_type": "light",
        "room": "Test",
        "state": "off",
        "online": True,
        "metadata": {"protocol": "logical"},
    })

    with pytest.raises(RuntimeError, match="No physical transport"):
        manager.set_state(logical.id, "on")
    assert manager.get_device(logical.id).state == "off"


def test_protocol_can_be_read_from_registered_device_metadata() -> None:
    result = PhysicalDeviceExecutor().execute(
        {
            "id": "http-device",
            "metadata": {"protocol": "http"},
        },
        "on",
    )
    assert result["protocol"] == "http"
    assert result["executed"] is False
    assert result["status"] == "configuration_required"


def test_unified_runtime_rejects_online_logical_device(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = UnifiedDeviceRuntime()
    monkeypatch.setattr(
        runtime,
        "list_devices",
        lambda: [{
            "id": "logical-light",
            "name": "Logical Light",
            "online": True,
            "state": "off",
            "protocol": "logical",
        }],
    )

    result = runtime.set_state("Logical Light", "on")
    assert result["status"] == "execution_failed"
    assert result["execution"]["executed"] is False


def test_unified_runtime_includes_registered_automation_devices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.automation.manager import device_manager
    from services.automation.models import Device
    from services.smart_home_runtime.store import smart_home_store

    monkeypatch.setattr(
        smart_home_store,
        "read",
        lambda: {"rooms": [], "devices": [], "scenes": []},
    )
    monkeypatch.setattr(
        device_manager,
        "list_devices",
        lambda: [Device(
            id="registered-light",
            name="Registered Light",
            device_type="light",
            room="Test",
            online=False,
        )],
    )

    devices = UnifiedDeviceRuntime().list_devices()
    assert len(devices) == 1
    assert devices[0]["id"] == "registered-light"
    assert devices[0]["runtime"] == "automation_devices"
    assert devices[0]["online"] is False


def test_empty_smart_automation_run_is_recorded_as_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = AutomationActionExecutor()
    monkeypatch.setattr(
        executor,
        "_record_run",
        lambda **values: {
            "status": values["status"],
            "results": values["results"],
        },
    )

    result = executor.execute_actions(
        rule={"id": "empty", "name": "Empty", "actions": []},
        context={},
    )
    assert result["status"] == "failed"
    assert "no actions" in result["results"][0]["error"].lower()


def test_scene_failure_does_not_increment_run_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene_module = importlib.import_module("services.automation.scene_manager")

    class OfflineManager:
        @staticmethod
        def set_state(device_id: str, state: str):
            raise RuntimeError("Device is offline.")

        @staticmethod
        def toggle(device_id: str):
            raise RuntimeError("Device is offline.")

    monkeypatch.setattr(scene_module, "device_manager", OfflineManager())
    manager = scene_module.SceneManager(tmp_path / "scenes.json")
    scene = manager.create({
        "name": "Offline scene",
        "actions": [{"type": "device_on", "device_id": "missing"}],
    })

    result = manager.execute(scene["id"])
    assert result["status"] == "failed"
    assert result["success_count"] == 0
    assert result["error_count"] == 1
    assert result["scene"]["run_count"] == 0
    assert result["scene"]["last_run_at"] is None


def test_static_notification_route_precedes_dynamic_notification_id_route() -> None:
    main = (ROOT / "main.py").read_text()
    final_include = main.index("app.include_router(mobile_notifications_final_router)")
    base_include = main.index("app.include_router(mobile_notifications_router)")
    assert final_include < base_include


def test_pwa_starts_and_caches_v126_product_shell() -> None:
    manifest = json.loads((ROOT / "dashboard/pwa/manifest.webmanifest").read_text())
    worker = (ROOT / "dashboard/pwa/sw.js").read_text()
    assert manifest["start_url"] == "/mobile?v126=1"
    assert any(item["url"].endswith("#nb-halo") for item in manifest["shortcuts"])
    assert "noorbrain-mobile-shell-v126.js" in worker
    assert "automation-center-v12.js" in worker
    assert "mobile-rules-v12.js" in worker


def test_halo_voice_uses_bundled_model_and_declares_transcriber_dependency() -> None:
    from services.halo_voice.routes import load_config

    config = load_config()
    model = Path(config["model"])
    assert model.is_absolute()
    assert model.exists()
    assert model.name == "faster-whisper-tiny.en"
    requirements = (ROOT / "requirements.txt").read_text().splitlines()
    assert "faster-whisper" in requirements


def test_android_apk_contains_real_native_recording_bridge() -> None:
    import zipfile

    apk = ROOT / "NoorBrainMobile-PERMANENT-MIC-FIX.apk"
    with zipfile.ZipFile(apk) as archive:
        app = archive.read("assets/public/app.js").decode("utf-8")
        plugins = json.loads(archive.read("assets/capacitor.plugins.json"))

    packages = {item["pkg"] for item in plugins}
    assert "@capgo/capacitor-audio-recorder" in packages
    assert "@capacitor/filesystem" in packages
    assert "requestPermissions()" in app
    assert "startRecording" in app
    assert "stopRecording" in app
    assert '"/api/halo-voice/transcribe-base64"' in app
    assert 'type: "noorbrain-native-transcript"' in app
