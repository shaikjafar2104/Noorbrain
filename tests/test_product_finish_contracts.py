from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from services.automation.manager import DeviceManager
from services.automation.scene_manager import SceneManager
from services.automation.storage import DeviceStorage
from services.smart_automation.store import AutomationStore


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
