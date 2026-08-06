from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .service import islamic_audio


router = APIRouter(prefix="/api/islamic-audio", tags=["Islamic Audio Control"])


@router.get("/health")
async def health() -> dict[str, Any]:
    items = await asyncio.to_thread(islamic_audio.catalog)
    return {
        "status": "healthy",
        "service": "islamic_audio_control",
        "version": "16.1.0",
        "media_count": len(items),
        "electronic_tts": False,
        "config": islamic_audio.read_config(),
    }


@router.get("/catalog")
async def catalog(search: str = Query(default="")) -> dict[str, Any]:
    items = await asyncio.to_thread(islamic_audio.catalog, search)
    return {"status": "ok", "count": len(items), "items": items}


@router.post("/play/{media_id}")
async def play(media_id: str) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(islamic_audio.play_item, media_id, "manual")
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except Exception as error:
        raise HTTPException(500, f"{type(error).__name__}: {error}") from error


@router.post("/play-query")
async def play_query(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    if not query:
        raise HTTPException(422, "Query is required.")
    try:
        return await asyncio.to_thread(islamic_audio.play_by_query, query, "manual")
    except LookupError as error:
        raise HTTPException(404, str(error)) from error


@router.get("/events")
async def events(after: int = Query(default=0, ge=0)) -> dict[str, Any]:
    event = islamic_audio.event_after(after)
    return {"status": "ok", "event": event}


@router.get("/config")
async def config() -> dict[str, Any]:
    return {"status": "ok", "config": islamic_audio.read_config()}


@router.patch("/config")
async def update_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return {"status": "updated", "config": islamic_audio.update_config(payload)}
