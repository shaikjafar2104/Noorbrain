from __future__ import annotations

import importlib
from io import BytesIO
from pathlib import Path

import pytest

from services.automation.manager import DeviceManager
from services.automation.scene_manager import SceneManager
from services.automation.storage import DeviceStorage
from services.smart_automation.store import AutomationStore


def test_media_list_create_edit_delete_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    media_module = importlib.import_module("services.media_library.media_manager")
    monkeypatch.setattr(media_module, "MEDIA_ROOT", tmp_path / "audio")
    monkeypatch.setattr(media_module, "DATABASE_PATH", tmp_path / "media.json")
    manager = media_module.MediaLibraryManager()

    assert manager.list_items() == []
    item = manager.save_upload(
        BytesIO(b"RIFF" + (b"\x00" * 1024)),
        "contract.wav",
        category="custom",
        display_name="Contract audio",
    )
    original_path = manager.get_file_path(item["id"])
    assert original_path.is_file()

    updated = manager.update_item(
        item["id"],
        name="Updated audio",
        category="islamic",
        metadata={"islamic_type": "dua"},
    )
    assert updated["name"] == "Updated audio"
    assert updated["category"] == "islamic"
    assert updated["metadata"] == {"islamic_type": "dua"}
    assert not original_path.exists()
    assert manager.get_file_path(item["id"]).is_file()

    manager.delete_item(item["id"])
    assert manager.list_items() == []


def test_device_list_create_edit_delete_contract(tmp_path: Path) -> None:
    manager = DeviceManager(DeviceStorage(tmp_path / "devices.json"))
    assert manager.list_devices() == []

    device = manager.create_device({
        "name": "Contract light",
        "device_type": "light",
        "room": "Test",
        "online": False,
        "metadata": {"protocol": "logical"},
    })
    assert manager.get_device(device.id).name == "Contract light"

    updated = manager.update_device(device.id, {"room": "Updated"})
    assert updated.room == "Updated"
    with pytest.raises(RuntimeError, match="offline"):
        manager.toggle(device.id)

    assert manager.delete_device(device.id) is True
    assert manager.list_devices() == []


def test_smart_rule_list_create_edit_toggle_delete_contract(tmp_path: Path) -> None:
    store = AutomationStore()
    store.path = tmp_path / "smart-rules.json"
    store.write({"schema_version": 1, "rules": [], "runs": []})

    assert store.list_rules() == []
    rule = store.create_rule({
        "name": "Contract rule",
        "trigger": {"type": "manual"},
        "actions": [{"type": "halo_speak", "message": "Test"}],
    })
    updated = store.update_rule(rule["id"], {"name": "Updated rule"})
    assert updated["name"] == "Updated rule"
    assert store.update_rule(rule["id"], {"enabled": False})["enabled"] is False
    assert store.delete_rule(rule["id"]) == 1
    assert store.list_rules() == []


def test_islamic_family_and_plugin_crud_contracts(tmp_path: Path) -> None:
    islamic_module = importlib.import_module("services.islamic_intelligence_v12.store")
    islamic = islamic_module.Store()
    islamic.path = tmp_path / "islamic.json"
    rule = islamic.add_rule({
        "name": "TEST Islamic rule",
        "event": "person_entered",
        "zone": "Test Zone",
        "message": "Test reminder",
    })
    assert islamic.patch_rule(rule["id"], {"enabled": False})["enabled"] is False
    assert islamic.evaluate({"event": "person_entered", "zone": "Test Zone"})["reminders"] == []
    assert islamic.patch_rule(rule["id"], {"enabled": True})["enabled"] is True
    assert len(islamic.evaluate({"event": "person_entered", "zone": "Test Zone"})["reminders"]) == 1
    assert islamic.delete_rule(rule["id"]) is True

    family_module = importlib.import_module("services.family_intelligence_v11.store")
    family = family_module.FamilyIntelligenceStore()
    family.path = tmp_path / "family.json"
    member = family.add_member({"name": "TEST Member", "role": "guest"})
    assert family.update_member(member["id"], {"role": "family"})["role"] == "family"
    assert family.update_privacy({"recognition_enabled": False})["recognition_enabled"] is False
    assert family.delete_member(member["id"]) is True
    assert family.overview()["members"] == []

    plugin_module = importlib.import_module("services.plugin_platform_v13.store")
    plugins = plugin_module.PluginRegistry()
    plugins.path = tmp_path / "plugins.json"
    plugin = plugins.install({
        "id": "test_plugin",
        "name": "TEST Plugin",
        "version": "1.0.0",
        "permissions": ["read_devices"],
    })
    assert plugins.enable(plugin["id"], True)["enabled"] is True
    assert plugins.enable(plugin["id"], False)["enabled"] is False
    assert plugins.delete(plugin["id"]) is True
    assert plugins.overview()["plugins"] == []


def test_scene_and_routine_crud_and_failed_run_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene_module = importlib.import_module("services.automation.scene_manager")
    routine_module = importlib.import_module("services.automation.routine_scheduler")

    class OfflineDevices:
        @staticmethod
        def set_state(device_id: str, state: str):
            raise RuntimeError("Device is offline.")

        @staticmethod
        def toggle(device_id: str):
            raise RuntimeError("Device is offline.")

    monkeypatch.setattr(scene_module, "device_manager", OfflineDevices())
    scenes = SceneManager(tmp_path / "scenes.json")
    monkeypatch.setattr(routine_module, "scene_manager", scenes)
    routines = routine_module.RoutineScheduler(tmp_path / "routines.json")

    scene = scenes.create({
        "name": "Contract scene",
        "actions": [{"type": "device_on", "device_id": "offline"}],
    })
    assert scenes.update(scene["id"], {"enabled": False})["enabled"] is False
    assert scenes.update(scene["id"], {"enabled": True})["enabled"] is True

    routine = routines.create({
        "name": "Contract routine",
        "scene_id": scene["id"],
        "schedule": "08:00",
    })
    assert routines.update(routine["id"], {"schedule": "09:00"})["schedule"] == "09:00"

    result = routines.run_now(routine["id"])
    assert result["status"] == "failed"
    persisted = next(item for item in routines.list() if item["id"] == routine["id"])
    assert persisted["run_count"] == 0
    assert persisted["last_run_at"] is None

    assert routines.delete(routine["id"]) is True
    assert scenes.delete(scene["id"]) is True
    assert routines.list() == []
    assert scenes.list() == []
