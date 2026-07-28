from __future__ import annotations

from typing import Any

from .models import Device, DeviceCreate, DeviceState, utc_now_iso
from .storage import DeviceStorage


class DeviceManager:
    def __init__(self, storage: DeviceStorage | None = None) -> None:
        self.storage = storage or DeviceStorage()

    def list_devices(self) -> list[Device]:
        return self.storage.list()

    def get_device(self, device_id: str) -> Device:
        device = self.storage.get(device_id)
        if device is None:
            raise KeyError(f"Device not found: {device_id}")
        return device

    def create_device(self, payload: DeviceCreate | dict[str, Any]) -> Device:
        return self.storage.create(payload)

    def update_device(self, device_id: str, patch: dict[str, Any]) -> Device:
        devices = self.storage.list()
        index = next((i for i, item in enumerate(devices) if item.id == device_id), None)
        if index is None:
            raise KeyError(f"Device not found: {device_id}")

        current = devices[index].model_dump()
        protected = {"id", "created_at"}
        for key, value in patch.items():
            if key not in protected and value is not None:
                current[key] = value

        current["updated_at"] = utc_now_iso()
        updated = Device.model_validate(current)
        devices[index] = updated
        self.storage.replace_all(devices)
        return updated

    def delete_device(self, device_id: str) -> bool:
        return self.storage.delete(device_id)

    def set_state(self, device_id: str, state: DeviceState) -> Device:
        return self.update_device(device_id, {"state": state})

    def toggle(self, device_id: str) -> Device:
        device = self.get_device(device_id)
        next_state = DeviceState.OFF if device.state == DeviceState.ON else DeviceState.ON
        return self.set_state(device_id, next_state)

    def stats(self) -> dict[str, Any]:
        devices = self.storage.list()
        by_type: dict[str, int] = {}
        by_room: dict[str, int] = {}

        for device in devices:
            by_type[device.device_type.value] = by_type.get(device.device_type.value, 0) + 1
            by_room[device.room] = by_room.get(device.room, 0) + 1

        return {
            "status": "ok",
            "total": len(devices),
            "online": sum(1 for item in devices if item.online),
            "offline": sum(1 for item in devices if not item.online),
            "on": sum(1 for item in devices if item.state == DeviceState.ON),
            "off": sum(1 for item in devices if item.state == DeviceState.OFF),
            "unknown": sum(1 for item in devices if item.state == DeviceState.UNKNOWN),
            "by_type": by_type,
            "by_room": by_room,
            "storage": self.storage.integrity_check(),
        }


device_manager = DeviceManager()
