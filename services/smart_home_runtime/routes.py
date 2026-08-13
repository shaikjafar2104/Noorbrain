from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Body, HTTPException
from .store import smart_home_store
from services.unified_device_runtime.service import unified_device_runtime

router = APIRouter(prefix="/api/smart-home-runtime", tags=["Smart Home Runtime"])

@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "service": "smart_home_runtime", "version": "3.3-c3", **smart_home_store.summary()}

@router.get("/summary")
def summary() -> dict[str, Any]:
    return smart_home_store.summary()

@router.get("/graph")
def graph() -> dict[str, Any]:
    data = smart_home_store.read()
    data["devices"] = unified_device_runtime.list_devices()
    return {"status": "ok", **data}

@router.post("/rooms")
def add_room(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "Room name is required.")
    data = smart_home_store.read()
    if not any(r.get("name","").casefold() == name.casefold() for r in data["rooms"]):
        data["rooms"].append({"id": name.casefold().replace(" ", "-"), "name": name})
        smart_home_store.write(data)
    return {"status": "ok", "room": name}

@router.post("/devices")
def add_device(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "Device name is required.")
    data = smart_home_store.read()
    device = {
        "id": str(payload.get("id") or name.casefold().replace(" ", "-")),
        "name": name,
        "room": payload.get("room"),
        "type": payload.get("type", "generic"),
        "state": payload.get("state", "off"),
        "online": bool(payload.get("online", False)),

        # V10.3 physical transport
        "protocol": payload.get(
            "protocol",
            payload.get("transport", "logical"),
        ),
        "base_url": payload.get("base_url"),
        "ip_address": payload.get("ip_address"),
        "command_topic": payload.get("command_topic"),
        "endpoints": dict(payload.get("endpoints") or {}),
        "metadata": dict(payload.get("metadata") or {}),
    }
    data["devices"] = [d for d in data["devices"] if d.get("id") != device["id"]]
    data["devices"].append(device)
    smart_home_store.write(data)
    return {"status": "ok", "device": device}

@router.post("/devices/{device_id}/state")
def set_state(device_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        result = unified_device_runtime.set_state_by_id(
            device_id,
            str(payload.get("state") or ""),
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    if result.get("status") == "not_found":
        raise HTTPException(404, "Device not found.")
    if result.get("status") != "ok":
        reason = result.get("execution", {}).get("reason")
        raise HTTPException(409, reason or "Physical device execution failed.")

    return result
