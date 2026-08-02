from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/sprint8-release",
    tags=["Sprint 8 Production Release"],
)

PROJECT = Path(__file__).resolve().parents[2]


def release_manifest() -> dict[str, Any]:
    path = PROJECT / "data" / "sprint8_release.json"
    if not path.is_file():
        return {"status": "missing", "version": "8.6.0"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "version": "8.6.0"}


@router.get("/health")
async def health() -> dict[str, Any]:
    manifest = release_manifest()
    return {
        "status": "healthy" if manifest.get("status") == "production" else "degraded",
        "service": "sprint8_production_release",
        "version": "8.6.0",
        "release": manifest,
    }


@router.get("/status")
async def status() -> dict[str, Any]:
    required = {
        "decision_engine": PROJECT / "installer" / "sprint8" / "batch_8A1.py",
        "routine_intelligence": PROJECT / "services" / "routine_intelligence_v8" / "routes.py",
        "voice_stability": PROJECT / "dashboard" / "js" / "sprint8c-voice-repeat-guard.js",
        "conversation_memory": PROJECT / "services" / "halo_conversation_memory_v8" / "routes.py",
        "voice_context": PROJECT / "services" / "halo_voice_context_v8" / "routes.py",
        "ai_dashboard": PROJECT / "dashboard" / "js" / "sprint8e1-ai-dashboard.js",
        "mobile_ai": PROJECT / "dashboard" / "js" / "sprint8e2-mobile-ai.js",
    }
    components = {
        name: {"installed": path.exists()}
        for name, path in required.items()
    }
    installed = sum(1 for item in components.values() if item["installed"])
    return {
        "status": "production" if installed == len(components) else "incomplete",
        "version": "8.6.0",
        "installed_components": installed,
        "total_components": len(components),
        "components": components,
        "manifest": release_manifest(),
    }
