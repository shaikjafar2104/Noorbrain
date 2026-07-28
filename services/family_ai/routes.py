from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Body, HTTPException
from .store import family_store

router = APIRouter(prefix="/api/family-ai", tags=["Family AI"])

@router.get("/health")
def health() -> dict[str, Any]:
    data = family_store.read()
    return {"status": "healthy", "service": "family_ai", "version": "3.5-c5", "profile_count": len(data["profiles"])}

@router.get("/profiles")
def profiles() -> dict[str, Any]:
    data = family_store.read()
    return {"status": "ok", "count": len(data["profiles"]), "profiles": data["profiles"]}

@router.post("/profiles")
def add_profile(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "Profile name is required.")
    data = family_store.read()
    profile = {
        "id": str(payload.get("id") or name.casefold().replace(" ", "-")),
        "name": name,
        "role": payload.get("role", "family"),
        "language": payload.get("language", "en"),
        "voice_profile": payload.get("voice_profile"),
        "preferences": dict(payload.get("preferences") or {}),
    }
    data["profiles"] = [p for p in data["profiles"] if p.get("id") != profile["id"]]
    data["profiles"].append(profile)
    family_store.write(data)
    return {"status": "ok", "profile": profile}

@router.get("/profiles/{profile_id}")
def profile(profile_id: str) -> dict[str, Any]:
    data = family_store.read()
    item = next((p for p in data["profiles"] if p.get("id") == profile_id), None)
    if not item:
        raise HTTPException(404, "Profile not found.")
    return {"status": "ok", "profile": item}
