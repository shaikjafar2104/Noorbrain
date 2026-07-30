from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix="/api/smart-home-v3", tags=["Smart Home v3"])

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "smart_home_v3.json"

DEFAULT: dict[str, Any] = {
    "version": 1,
    "rooms": [
        {"id": "hall", "name": "Hall", "icon": "🛋️"},
        {"id": "kitchen", "name": "Kitchen", "icon": "🍳"},
        {"id": "bedroom", "name": "Bedroom", "icon": "🛏️"},
        {"id": "prayer-room", "name": "Prayer Room", "icon": "🕌"},
    ],
    "devices": [],
    "scenes": [],
    "favorites": [],
}


def read_store() -> dict[str, Any]:
    STORE.parent.mkdir(parents=True, exist_ok=True)

    if not STORE.exists():
        write_store(DEFAULT.copy())
        return DEFAULT.copy()

    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    result = DEFAULT.copy()
    if isinstance(data, dict):
        result.update(data)

    result.setdefault("rooms", [])
    result.setdefault("devices", [])
    result.setdefault("scenes", [])
    result.setdefault("favorites", [])
    return result


def write_store(data: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    temp = STORE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(STORE)


def normalize_state(value: Any) -> str:
    return "on" if str(value).lower() in {"on", "true", "1"} else "off"


def call_webhook(url: str, payload: dict[str, Any]) -> None:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=4) as response:
        if response.status >= 400:
            raise RuntimeError(f"Webhook HTTP {response.status}")


@router.get("/health")
def health() -> dict[str, Any]:
    data = read_store()
    return {
        "status": "healthy",
        "service": "smart_home_v3",
        "version": "3.0.0",
        "rooms": len(data["rooms"]),
        "devices": len(data["devices"]),
        "scenes": len(data["scenes"]),
    }


@router.get("/state")
def state() -> dict[str, Any]:
    return {"status": "ok", "home": read_store()}


@router.post("/rooms")
def add_room(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    icon = str(payload.get("icon") or "🏠").strip()

    if not name:
        raise HTTPException(status_code=422, detail="Room name is required.")

    data = read_store()
    room = {
        "id": uuid.uuid4().hex[:10],
        "name": name,
        "icon": icon,
    }
    data["rooms"].append(room)
    write_store(data)
    return {"status": "created", "room": room}


@router.post("/devices")
def add_device(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    device_type = str(payload.get("type") or "switch").strip()
    room_id = str(payload.get("room_id") or "").strip()
    webhook_on = str(payload.get("webhook_on") or "").strip()
    webhook_off = str(payload.get("webhook_off") or "").strip()

    if not name:
        raise HTTPException(status_code=422, detail="Device name is required.")

    data = read_store()
    device = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "type": device_type,
        "room_id": room_id,
        "state": "off",
        "online": True,
        "webhook_on": webhook_on,
        "webhook_off": webhook_off,
    }
    data["devices"].append(device)
    write_store(data)
    return {"status": "created", "device": device}


@router.post("/devices/{device_id}/state")
def set_device_state(
    device_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    requested = normalize_state(payload.get("state"))
    data = read_store()

    device = next(
        (item for item in data["devices"] if item.get("id") == device_id),
        None,
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    webhook = device.get("webhook_on") if requested == "on" else device.get("webhook_off")

    if webhook:
        try:
            call_webhook(
                webhook,
                {
                    "device_id": device_id,
                    "state": requested,
                    "source": "NoorBrain",
                },
            )
            device["online"] = True
        except Exception as exc:
            device["online"] = False
            write_store(data)
            raise HTTPException(
                status_code=502,
                detail=f"Device webhook failed: {exc}",
            )

    device["state"] = requested
    write_store(data)
    return {"status": "updated", "device": device}


@router.post("/devices/{device_id}/toggle")
def toggle_device(device_id: str) -> dict[str, Any]:
    data = read_store()
    device = next(
        (item for item in data["devices"] if item.get("id") == device_id),
        None,
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    requested = "off" if device.get("state") == "on" else "on"
    return set_device_state(device_id, {"state": requested})


@router.delete("/devices/{device_id}")
def delete_device(device_id: str) -> dict[str, Any]:
    data = read_store()
    before = len(data["devices"])
    data["devices"] = [
        item for item in data["devices"] if item.get("id") != device_id
    ]

    if len(data["devices"]) == before:
        raise HTTPException(status_code=404, detail="Device not found.")

    data["favorites"] = [
        item for item in data["favorites"] if item != device_id
    ]
    write_store(data)
    return {"status": "deleted", "device_id": device_id}


@router.post("/favorites/{device_id}")
def toggle_favorite(device_id: str) -> dict[str, Any]:
    data = read_store()

    if not any(item.get("id") == device_id for item in data["devices"]):
        raise HTTPException(status_code=404, detail="Device not found.")

    if device_id in data["favorites"]:
        data["favorites"].remove(device_id)
        favorite = False
    else:
        data["favorites"].append(device_id)
        favorite = True

    write_store(data)
    return {"status": "updated", "device_id": device_id, "favorite": favorite}


@router.post("/scenes")
def add_scene(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    actions = payload.get("actions") or []

    if not name:
        raise HTTPException(status_code=422, detail="Scene name is required.")

    if not isinstance(actions, list):
        raise HTTPException(status_code=422, detail="Scene actions must be a list.")

    data = read_store()
    scene = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "icon": str(payload.get("icon") or "⚡"),
        "actions": actions,
    }
    data["scenes"].append(scene)
    write_store(data)
    return {"status": "created", "scene": scene}


@router.post("/scenes/{scene_id}/run")
def run_scene(scene_id: str) -> dict[str, Any]:
    data = read_store()
    scene = next(
        (item for item in data["scenes"] if item.get("id") == scene_id),
        None,
    )
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found.")

    results = []

    for action in scene.get("actions", []):
        device_id = str(action.get("device_id") or "")
        requested = normalize_state(action.get("state"))

        try:
            result = set_device_state(device_id, {"state": requested})
            results.append({
                "device_id": device_id,
                "status": "ok",
                "state": result["device"]["state"],
            })
        except HTTPException as exc:
            results.append({
                "device_id": device_id,
                "status": "error",
                "detail": exc.detail,
            })

    return {"status": "completed", "scene": scene, "results": results}
