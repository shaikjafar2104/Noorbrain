from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(
    prefix="/api/islamic-center-v5",
    tags=["Islamic Center v5"],
)

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "islamic_center_v5.json"

DEFAULT: dict[str, Any] = {
    "version": 1,
    "settings": {
        "enabled": True,
        "location": "Toronto",
        "calculation_method": "ISNA",
        "madhab": "Hanafi",
        "voice_reminders": True,
        "family_reminders": True,
        "ramadan_mode": False,
    },
    "prayers": {
        "Fajr": "05:30",
        "Sunrise": "07:00",
        "Dhuhr": "13:15",
        "Asr": "16:45",
        "Maghrib": "19:30",
        "Isha": "21:00",
    },
    "azkar": [
        {
            "id": "morning",
            "title": "Morning Azkar",
            "category": "Morning",
            "enabled": True,
        },
        {
            "id": "evening",
            "title": "Evening Azkar",
            "category": "Evening",
            "enabled": True,
        },
    ],
    "duas": [
        {
            "id": "leaving-home",
            "title": "Leaving Home",
            "text": "Bismillahi tawakkaltu alallah.",
            "enabled": True,
        },
        {
            "id": "entering-home",
            "title": "Entering Home",
            "text": "Bismillahi walajna wa bismillahi kharajna.",
            "enabled": True,
        },
    ],
    "reminders": [],
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

    result.setdefault("settings", DEFAULT["settings"].copy())
    result.setdefault("prayers", DEFAULT["prayers"].copy())
    result.setdefault("azkar", [])
    result.setdefault("duas", [])
    result.setdefault("reminders", [])

    return result


def write_store(data: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    temp = STORE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(STORE)


def minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


def prayer_state(prayers: dict[str, str]) -> dict[str, Any]:
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    ordered = [
        (name, time_value)
        for name, time_value in prayers.items()
        if name != "Sunrise"
    ]

    ordered.sort(key=lambda item: minutes(item[1]))

    next_name = ordered[0][0]
    next_time = ordered[0][1]
    current_name = ordered[-1][0]

    for index, (name, time_value) in enumerate(ordered):
        prayer_minutes = minutes(time_value)

        if current_minutes < prayer_minutes:
            next_name = name
            next_time = time_value
            current_name = ordered[index - 1][0] if index > 0 else ordered[-1][0]
            break

    delta = minutes(next_time) - current_minutes

    if delta < 0:
        delta += 24 * 60

    return {
        "current": current_name,
        "next": next_name,
        "next_time": next_time,
        "countdown_minutes": delta,
    }


@router.get("/health")
def health() -> dict[str, Any]:
    data = read_store()

    return {
        "status": "healthy",
        "service": "islamic_center_v5",
        "version": "5.0.0",
        "reminders": len(data["reminders"]),
        "duas": len(data["duas"]),
        "azkar": len(data["azkar"]),
    }


@router.get("/state")
def state() -> dict[str, Any]:
    data = read_store()

    return {
        "status": "ok",
        "islamic_center": data,
        "prayer_state": prayer_state(data["prayers"]),
    }


@router.post("/settings")
def update_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    data = read_store()
    data["settings"].update(payload)
    write_store(data)

    return {
        "status": "updated",
        "settings": data["settings"],
    }


@router.post("/prayers")
def update_prayers(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    data = read_store()

    for name, value in payload.items():
        if name not in DEFAULT["prayers"]:
            continue

        text = str(value).strip()

        try:
            minutes(text)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid time for {name}.",
            ) from exc

        data["prayers"][name] = text

    write_store(data)

    return {
        "status": "updated",
        "prayers": data["prayers"],
        "prayer_state": prayer_state(data["prayers"]),
    }


@router.post("/reminders")
def add_reminder(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    time_value = str(payload.get("time") or "").strip()
    reminder_type = str(payload.get("type") or "custom").strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Reminder title is required.",
        )

    if time_value:
        try:
            minutes(time_value)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail="Reminder time must use HH:MM.",
            ) from exc

    data = read_store()

    reminder = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "time": time_value,
        "type": reminder_type,
        "enabled": bool(payload.get("enabled", True)),
        "voice": bool(payload.get("voice", True)),
        "family": bool(payload.get("family", False)),
    }

    data["reminders"].append(reminder)
    write_store(data)

    return {
        "status": "created",
        "reminder": reminder,
    }


@router.post("/reminders/{reminder_id}/toggle")
def toggle_reminder(
    reminder_id: str,
) -> dict[str, Any]:
    data = read_store()

    reminder = next(
        (
            item
            for item in data["reminders"]
            if item.get("id") == reminder_id
        ),
        None,
    )

    if reminder is None:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found.",
        )

    reminder["enabled"] = not bool(reminder.get("enabled", True))
    write_store(data)

    return {
        "status": "updated",
        "reminder": reminder,
    }


@router.delete("/reminders/{reminder_id}")
def delete_reminder(
    reminder_id: str,
) -> dict[str, Any]:
    data = read_store()
    before = len(data["reminders"])

    data["reminders"] = [
        item
        for item in data["reminders"]
        if item.get("id") != reminder_id
    ]

    if len(data["reminders"]) == before:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found.",
        )

    write_store(data)

    return {
        "status": "deleted",
        "reminder_id": reminder_id,
    }


@router.post("/items/{item_type}/{item_id}/toggle")
def toggle_item(
    item_type: str,
    item_id: str,
) -> dict[str, Any]:
    if item_type not in {"duas", "azkar"}:
        raise HTTPException(
            status_code=422,
            detail="Unsupported item type.",
        )

    data = read_store()

    item = next(
        (
            value
            for value in data[item_type]
            if value.get("id") == item_id
        ),
        None,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found.",
        )

    item["enabled"] = not bool(item.get("enabled", True))
    write_store(data)

    return {
        "status": "updated",
        "item": item,
    }
