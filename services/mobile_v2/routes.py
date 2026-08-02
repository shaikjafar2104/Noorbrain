from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix="/api/mobile-v2", tags=["Mobile v2"])

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "mobile_v2.json"

DEFAULT = {
    "version": 1,
    "cameras": [],
    "rooms": ["Hall", "Kitchen", "Bedroom"],
}


def _read() -> dict[str, Any]:
    STORE.parent.mkdir(parents=True, exist_ok=True)

    if not STORE.exists():
        _write(DEFAULT.copy())
        return DEFAULT.copy()

    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    result = DEFAULT.copy()
    if isinstance(data, dict):
        result.update(data)

    result.setdefault("cameras", [])
    result.setdefault("rooms", [])
    return result


def _write(data: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    temp = STORE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(STORE)


@router.get("/health")
async def health() -> dict[str, Any]:
    data = await asyncio.to_thread(_read)

    return {
        "status": "healthy",
        "service": "mobile_v2",
        "version": "2.0.0",
        "camera_count": len(data["cameras"]),
    }


@router.get("/config")
async def get_config() -> dict[str, Any]:
    return {
        "status": "ok",
        "config": await asyncio.to_thread(_read),
    }


@router.post("/cameras")
async def add_camera(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    stream_url = str(payload.get("stream_url") or "").strip()
    room = str(payload.get("room") or "Home").strip()

    if not name:
        raise HTTPException(status_code=422, detail="Camera name is required.")

    if not stream_url:
        raise HTTPException(status_code=422, detail="Camera stream URL is required.")

    if not (
        stream_url.startswith("/")
        or stream_url.startswith("http://")
        or stream_url.startswith("https://")
    ):
        raise HTTPException(
            status_code=422,
            detail="Camera URL must start with /, http:// or https://",
        )

    data = await asyncio.to_thread(_read)

    camera = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "room": room,
        "stream_url": stream_url,
        "enabled": True,
    }

    data["cameras"].append(camera)
    await asyncio.to_thread(_write, data)

    return {"status": "created", "camera": camera}


@router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str) -> dict[str, Any]:
    data = await asyncio.to_thread(_read)
    before = len(data["cameras"])

    data["cameras"] = [
        item
        for item in data["cameras"]
        if item.get("id") != camera_id
    ]

    if len(data["cameras"]) == before:
        raise HTTPException(status_code=404, detail="Camera not found.")

    await asyncio.to_thread(_write, data)

    return {"status": "deleted", "camera_id": camera_id}
