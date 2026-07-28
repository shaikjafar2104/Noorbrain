from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, status

from .manager import device_manager
from .models import DeviceCreate, DeviceState

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.get("/health")
def devices_health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "automation_devices",
        "storage": device_manager.storage.integrity_check(),
    }


@router.get("/stats")
def device_stats() -> dict[str, Any]:
    return device_manager.stats()


@router.get("")
def list_devices() -> dict[str, Any]:
    devices = device_manager.list_devices()
    return {
        "status": "ok",
        "count": len(devices),
        "devices": [item.model_dump(mode="json") for item in devices],
    }


@router.get("/{device_id}")
def get_device(device_id: str) -> dict[str, Any]:
    try:
        device = device_manager.get_device(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "ok", "device": device.model_dump(mode="json")}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_device(payload: DeviceCreate) -> dict[str, Any]:
    try:
        device = device_manager.create_device(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"status": "created", "device": device.model_dump(mode="json")}


@router.put("/{device_id}")
@router.patch("/{device_id}")
def update_device(
    device_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        device = device_manager.update_device(device_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"status": "updated", "device": device.model_dump(mode="json")}


@router.delete("/{device_id}")
def delete_device(device_id: str) -> dict[str, Any]:
    if not device_manager.delete_device(device_id):
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    return {"status": "deleted", "device_id": device_id}


@router.post("/{device_id}/toggle")
def toggle_device(device_id: str) -> dict[str, Any]:
    try:
        device = device_manager.toggle(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "ok", "device": device.model_dump(mode="json")}


@router.post("/{device_id}/on")
def turn_device_on(device_id: str) -> dict[str, Any]:
    try:
        device = device_manager.set_state(device_id, DeviceState.ON)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "ok", "device": device.model_dump(mode="json")}


@router.post("/{device_id}/off")
def turn_device_off(device_id: str) -> dict[str, Any]:
    try:
        device = device_manager.set_state(device_id, DeviceState.OFF)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "ok", "device": device.model_dump(mode="json")}
