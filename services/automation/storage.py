from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from threading import RLock
from typing import Iterable
from .models import Device, DeviceCreate, utc_now_iso

class DeviceStorage:
    """Thread-safe, atomic JSON storage for NoorBrain devices."""
    def __init__(self, path: Path | str | None = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.path = Path(path) if path else project_root / "data" / "devices.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.path.exists():
            self._write_payload({"schema_version": 1, "devices": []})

    def _read_payload(self) -> dict:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Cannot read device storage {self.path}: {exc}") from exc
            if not isinstance(payload, dict): raise RuntimeError("Device storage root must be a JSON object.")
            if payload.get("schema_version") != 1: raise RuntimeError("Unsupported devices.json schema version.")
            if not isinstance(payload.get("devices"), list): raise RuntimeError("Device storage 'devices' must be a list.")
            return payload

    def _write_payload(self, payload: dict) -> None:
        with self._lock:
            fd, temporary_name = tempfile.mkstemp(prefix="devices-", suffix=".tmp", dir=str(self.path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush(); os.fsync(handle.fileno())
                os.replace(temporary_name, self.path)
            finally:
                if os.path.exists(temporary_name): os.unlink(temporary_name)

    def list(self) -> list[Device]:
        return [Device.model_validate(item) for item in self._read_payload()["devices"]]

    def get(self, device_id: str) -> Device | None:
        return next((item for item in self.list() if item.id == device_id), None)

    def create(self, data: DeviceCreate | dict) -> Device:
        request = data if isinstance(data, DeviceCreate) else DeviceCreate.model_validate(data)
        device = Device(**request.model_dump())
        devices = self.list()
        if any(existing.name.casefold() == device.name.casefold() for existing in devices):
            raise ValueError(f"A device named '{device.name}' already exists.")
        devices.append(device)
        self.replace_all(devices)
        return device

    def replace_all(self, devices: Iterable[Device]) -> None:
        validated = [Device.model_validate(item) for item in devices]
        self._write_payload({"schema_version": 1, "updated_at": utc_now_iso(), "devices": [item.model_dump(mode="json") for item in validated]})

    def delete(self, device_id: str) -> bool:
        devices = self.list(); remaining = [item for item in devices if item.id != device_id]
        if len(remaining) == len(devices): return False
        self.replace_all(remaining); return True

    def integrity_check(self) -> dict:
        devices = self.list(); ids = [item.id for item in devices]
        return {"status": "ok", "path": str(self.path), "schema_version": 1, "device_count": len(devices), "unique_ids": len(ids) == len(set(ids))}
