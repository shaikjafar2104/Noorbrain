from __future__ import annotations

import asyncio
import json
import re
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix="/api/halo-oneclick", tags=["HALO One Click"])

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
STORE = DATA_DIR / "home_devices.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE.exists():
        data = {"version": 1, "devices": [], "updated_at": _now()}
        STORE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        data = {"version": 1, "devices": [], "updated_at": _now()}
    data.setdefault("devices", [])
    return data


def _write(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(STORE)


def _public(device: dict[str, Any]) -> dict[str, Any]:
    item = dict(device)
    item.pop("token", None)
    return item


def _find(data: dict[str, Any], device_id: str) -> dict[str, Any] | None:
    return next((x for x in data["devices"] if x.get("id") == device_id), None)


def _http_call(device: dict[str, Any], action: str) -> dict[str, Any]:
    config = device.get("connection") or {}
    base_url = str(config.get("base_url") or "").rstrip("/")
    endpoint = str(config.get(f"{action}_endpoint") or "").strip()
    if not base_url or not endpoint:
        return {"ok": True, "mode": "local-state"}

    url = base_url + (endpoint if endpoint.startswith("/") else "/" + endpoint)
    method = str(config.get("method") or "POST").upper()
    headers = {"Accept": "application/json"}
    token = str(config.get("token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=b"{}" if method in {"POST", "PUT", "PATCH"} else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return {"ok": True, "status_code": response.status, "response": body}
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Device returned HTTP {exc.code}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Device connection failed: {exc}")


@router.get("/health")
async def health() -> dict[str, Any]:
    data = await asyncio.to_thread(_read)
    return {
        "status": "healthy",
        "service": "halo_oneclick",
        "version": "1.0.0",
        "device_count": len(data["devices"]),
    }


@router.get("/devices")
async def list_devices() -> dict[str, Any]:
    data = await asyncio.to_thread(_read)
    return {"status": "ok", "devices": [_public(x) for x in data["devices"]]}


@router.post("/devices")
async def add_device(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    room = str(payload.get("room") or "Home").strip()
    device_type = str(payload.get("type") or "switch").strip().lower()
    protocol = str(payload.get("protocol") or "local").strip().lower()

    if not name:
        raise HTTPException(status_code=422, detail="Device name is required.")

    data = await asyncio.to_thread(_read)
    device = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "room": room,
        "type": device_type,
        "protocol": protocol,
        "enabled": True,
        "state": "off",
        "online": True if protocol == "local" else None,
        "connection": {
            "base_url": str(payload.get("base_url") or "").strip(),
            "on_endpoint": str(payload.get("on_endpoint") or "/on").strip(),
            "off_endpoint": str(payload.get("off_endpoint") or "/off").strip(),
            "method": str(payload.get("method") or "POST").upper(),
            "token": str(payload.get("token") or "").strip(),
        },
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["devices"].append(device)
    await asyncio.to_thread(_write, data)
    return {"status": "created", "device": _public(device)}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str) -> dict[str, Any]:
    data = await asyncio.to_thread(_read)
    before = len(data["devices"])
    data["devices"] = [x for x in data["devices"] if x.get("id") != device_id]
    if len(data["devices"]) == before:
        raise HTTPException(status_code=404, detail="Device not found.")
    await asyncio.to_thread(_write, data)
    return {"status": "deleted", "device_id": device_id}


@router.post("/devices/{device_id}/{action}")
async def control_device(device_id: str, action: str) -> dict[str, Any]:
    action = action.lower()
    if action not in {"on", "off", "toggle"}:
        raise HTTPException(status_code=422, detail="Unsupported action.")

    data = await asyncio.to_thread(_read)
    device = _find(data, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    resolved = action
    if action == "toggle":
        resolved = "off" if device.get("state") == "on" else "on"

    remote = {"ok": True, "mode": "local-state"}
    if device.get("protocol") == "http":
        remote = await asyncio.to_thread(_http_call, device, resolved)

    device["state"] = resolved
    device["online"] = True
    device["updated_at"] = _now()
    await asyncio.to_thread(_write, data)
    return {"status": "updated", "action": resolved, "device": _public(device), "remote": remote}


def _match_device(message: str, devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    lowered = message.lower()
    ranked = sorted(devices, key=lambda x: len(str(x.get("name", ""))), reverse=True)
    for device in ranked:
        name = str(device.get("name") or "").lower()
        if name and name in lowered:
            return device
    for device in ranked:
        room = str(device.get("room") or "").lower()
        kind = str(device.get("type") or "").lower()
        if room and kind and room in lowered and kind in lowered:
            return device
    return None


@router.post("/command")
async def command(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    message = str(payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="Command is required.")

    data = await asyncio.to_thread(_read)
    lowered = message.lower()
    device = _match_device(message, data["devices"])

    on_words = ("turn on", "switch on", "on karo", "chalu karo", "start ")
    off_words = ("turn off", "switch off", "off karo", "band karo", "stop ")

    if device and any(word in lowered for word in on_words + off_words):
        action = "off" if any(word in lowered for word in off_words) else "on"
        result = await control_device(device["id"], action)
        return {
            "status": "handled",
            "source": "device",
            "reply": f"{device['name']} {action} kar diya.",
            "result": result,
        }

    if re.search(r"\b(list|show|dikhao)\b.*\b(device|devices|home)\b", lowered):
        names = [x["name"] for x in data["devices"]]
        reply = "Registered devices: " + ", ".join(names) if names else "Abhi koi home device add nahi hai."
        return {"status": "handled", "source": "devices", "reply": reply}

    # Unknown commands use the existing NoorBrain HALO endpoint in the browser.
    return {
        "status": "forward",
        "source": "halo",
        "reply": "",
        "message": message,
    }
