from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix="/api/halo-ai-v4", tags=["HALO AI v4"])

ROOT = Path(__file__).resolve().parents[2]
MEMORY = ROOT / "data" / "halo_ai_v4_memory.json"

DEFAULT: dict[str, Any] = {
    "version": 1,
    "conversations": [],
    "profiles": {
        "default": {
            "name": "Home",
            "language": "auto",
            "voice_enabled": True,
            "wake_phrase": "halo",
        }
    },
    "active_profile": "default",
}


def read_memory() -> dict[str, Any]:
    MEMORY.parent.mkdir(parents=True, exist_ok=True)

    if not MEMORY.exists():
        write_memory(DEFAULT.copy())
        return DEFAULT.copy()

    try:
        data = json.loads(MEMORY.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    result = DEFAULT.copy()
    if isinstance(data, dict):
        result.update(data)

    result.setdefault("conversations", [])
    result.setdefault("profiles", DEFAULT["profiles"].copy())
    result.setdefault("active_profile", "default")
    return result


def write_memory(data: dict[str, Any]) -> None:
    MEMORY.parent.mkdir(parents=True, exist_ok=True)
    temp = MEMORY.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(MEMORY)


def add_message(role: str, text: str, meta: dict[str, Any] | None = None) -> None:
    data = read_memory()
    data["conversations"].append(
        {
            "role": role,
            "text": text,
            "time": int(time.time()),
            "meta": meta or {},
        }
    )
    data["conversations"] = data["conversations"][-200:]
    write_memory(data)


def command_intent(text: str) -> dict[str, Any]:
    clean = text.strip()
    lower = clean.lower()

    patterns = [
        (
            r"(?:turn|switch)\s+(?P<state>on|off)\s+(?P<device>.+)",
            "device_control",
        ),
        (
            r"(?P<device>.+)\s+(?P<state>on|off)\s+(?:karo|kar do|karna)",
            "device_control",
        ),
        (
            r"(?:show|open)\s+(?P<target>camera|vision|devices|prayer|automation|reminders)",
            "open_module",
        ),
    ]

    for pattern, intent in patterns:
        match = re.search(pattern, lower)
        if match:
            return {
                "intent": intent,
                "entities": match.groupdict(),
                "confidence": 0.92,
            }

    if any(word in lower for word in ("prayer", "namaz", "salah", "fajr", "asr", "maghrib")):
        return {"intent": "prayer_query", "entities": {}, "confidence": 0.84}

    if any(word in lower for word in ("camera", "vision", "who is home", "ghar me kaun")):
        return {"intent": "vision_query", "entities": {}, "confidence": 0.82}

    return {"intent": "chat", "entities": {}, "confidence": 0.55}


@router.get("/health")
def health() -> dict[str, Any]:
    data = read_memory()
    return {
        "status": "healthy",
        "service": "halo_ai_v4",
        "version": "4.0.0",
        "memory_messages": len(data["conversations"]),
        "active_profile": data["active_profile"],
    }


@router.get("/memory")
def memory(limit: int = 50) -> dict[str, Any]:
    data = read_memory()
    limit = max(1, min(int(limit), 200))
    return {
        "status": "ok",
        "messages": data["conversations"][-limit:],
    }


@router.delete("/memory")
def clear_memory() -> dict[str, Any]:
    data = read_memory()
    data["conversations"] = []
    write_memory(data)
    return {"status": "cleared"}


@router.post("/intent")
def intent(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    text = str(payload.get("text") or "").strip()

    if not text:
        raise HTTPException(status_code=422, detail="Text is required.")

    result = command_intent(text)
    add_message("user", text, {"intent": result["intent"]})

    return {
        "status": "ok",
        "text": text,
        **result,
    }


@router.get("/profiles")
def profiles() -> dict[str, Any]:
    data = read_memory()
    return {
        "status": "ok",
        "active_profile": data["active_profile"],
        "profiles": data["profiles"],
    }


@router.post("/profiles/{profile_id}")
def save_profile(
    profile_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    data = read_memory()

    data["profiles"][profile_id] = {
        "name": str(payload.get("name") or profile_id),
        "language": str(payload.get("language") or "auto"),
        "voice_enabled": bool(payload.get("voice_enabled", True)),
        "wake_phrase": str(payload.get("wake_phrase") or "halo").strip(),
    }

    if payload.get("activate", False):
        data["active_profile"] = profile_id

    write_memory(data)

    return {
        "status": "saved",
        "profile_id": profile_id,
        "profile": data["profiles"][profile_id],
        "active_profile": data["active_profile"],
    }
