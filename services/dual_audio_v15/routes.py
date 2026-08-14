from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from services.playback_router import playback_router
from services.playback_router.router import PlaybackRoutingError


router = APIRouter(prefix="/api/dual-audio-v15", tags=["Legacy Pi Audio Compatibility"])
ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data" / "dual_audio_v15.json"
DEFAULT = {
    "version": "15.2.0",
    "input_mode": "pi",
    "output_mode": "pi",
    "pi_node_url": "http://192.168.2.29:8010",
    "target_node": "existing-pi-audio",
    "electronic_tts": False,
    "app_audio": False,
    "pi_audio": True,
}


def read() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    data.pop("node_token", None)
    data.pop("token", None)
    return {
        **DEFAULT,
        **data,
        "input_mode": "pi",
        "output_mode": "pi",
        "electronic_tts": False,
        "app_audio": False,
        "pi_audio": True,
        "target_node": str(data.get("target_node") or DEFAULT["target_node"]),
    }


def write(data: dict[str, Any]) -> dict[str, Any]:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    normalized = {**read(), **data, "input_mode": "pi", "output_mode": "pi", "app_audio": False, "pi_audio": True}
    CONFIG.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return normalized


@router.get("/health")
def health() -> dict[str, Any]:
    config = read()
    try:
        node = playback_router.health(config["target_node"])
    except PlaybackRoutingError as error:
        node = {"status": "offline", "detail": str(error)}
    return {"status": "healthy", "service": "dual_audio_v15", "version": "15.2.0", "config": config, "pi": node}


@router.get("/config")
def config() -> dict[str, Any]:
    return {"status": "ok", "config": read()}


@router.patch("/config")
def update(payload: dict = Body(...)) -> dict[str, Any]:
    target_node = str(payload.get("target_node") or read()["target_node"]).strip()
    if not target_node:
        raise HTTPException(422, "A target Raspberry Pi speaker is required")
    return {"status": "updated", "config": write({"target_node": target_node})}


@router.post("/play")
def play(payload: dict = Body(...)) -> dict[str, Any]:
    audio = str(payload.get("audio_base64") or "")
    if not audio:
        raise HTTPException(422, "Audio is required")
    try:
        base64.b64decode(audio, validate=True)
        result = playback_router.play({
            "target_node": str(payload.get("target_node") or read()["target_node"]),
            "type": "audio",
            "audio_base64": audio,
            "format": str(payload.get("format") or "wav"),
            "volume": payload.get("volume"),
        })
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except PlaybackRoutingError as error:
        raise HTTPException(503, str(error)) from error
    return {"status": "routed", "output_mode": "pi", "result": {"app": None, "pi": result}}


@router.post("/pi/record")
def record(payload: dict = Body(default={})) -> dict[str, Any]:
    seconds = max(1, min(int(payload.get("seconds", 4)), 15))
    target = str(payload.get("target_node") or read()["target_node"])
    try:
        return {"status": "captured", "recording": playback_router.record_once(target, seconds)}
    except PlaybackRoutingError as error:
        raise HTTPException(503, str(error)) from error
