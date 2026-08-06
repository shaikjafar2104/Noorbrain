from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from services.islamic_audio_rules.catalog import ROOT, catalog_items, sync_catalog
from services.islamic_audio_rules.playback import EVENTS, play_media_rule
from services.media_library.media_manager import MediaLibraryError
from services.reminder_rules.reminder_rules import reminder_rules


router = APIRouter(prefix="/api/islamic-audio-rules", tags=["Islamic Audio Rules"])


@router.get("/health")
def health() -> dict[str, Any]:
    result = sync_catalog()
    return {"status": "healthy", "service": "islamic_audio_rules", "version": "1.0.0", **result}


@router.get("/catalog")
def catalog() -> dict[str, Any]:
    items = catalog_items()
    return {
        "status": "ok",
        "count": len(items),
        "duas": [item for item in items if item.get("category") == "duas"],
        "azkar": [item for item in items if item.get("category") == "azkar"],
    }


@router.post("/sync")
def sync() -> dict[str, Any]:
    return {"status": "synced", **sync_catalog()}


@router.post("/play/{media_id}")
def play(media_id: str) -> dict[str, Any]:
    try:
        return play_media_rule(media_id)
    except (MediaLibraryError, OSError, KeyError) as error:
        raise HTTPException(404, str(error)) from error


@router.post("/rules", status_code=201)
def create_rule(payload: dict = Body(...)) -> dict[str, Any]:
    media_id = str(payload.get("media_id") or "").strip()
    item = next((row for row in catalog_items() if row.get("id") == media_id), None)
    if item is None:
        raise HTTPException(404, "Dua or Azkar audio not found")
    data = {
        "name": str(payload.get("name") or item.get("name") or "Islamic Reminder"),
        "trigger": str(payload.get("trigger") or "entered_zone"),
        "zone": str(payload.get("zone") or "").strip() or None,
        "message": str(payload.get("message") or item.get("name") or "Islamic reminder"),
        "cooldown_seconds": max(0, int(payload.get("cooldown_seconds", 1800))),
        "speak": False,
        "media_id": media_id,
        "enabled": bool(payload.get("enabled", True)),
    }
    try:
        rule = reminder_rules.create_rule(data)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return {"status": "created", "rule": rule, "media": item}


@router.get("/events")
def events(after: float = Query(default=0, ge=0)) -> dict[str, Any]:
    try:
        rows = json.loads(EVENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        rows = []
    return {"status": "ok", "events": [row for row in rows if float(row.get("timestamp", 0)) > after]}
