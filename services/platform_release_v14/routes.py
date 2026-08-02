from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/platform-release-v14",
    tags=["NoorBrain Production Release V14"],
)
PROJECT = Path(__file__).resolve().parents[2]


def component_paths() -> dict[str, Path]:
    return {
        "sprint8_ai": PROJECT / "data" / "sprint8_release.json",
        "sprint9_voice": PROJECT / "data" / "sprint9_release.json",
        "sprint10_whole_home": PROJECT / "services" / "whole_home_v10" / "routes.py",
        "sprint11_family": PROJECT / "services" / "family_intelligence_v11" / "routes.py",
        "sprint12_islamic": PROJECT / "services" / "islamic_intelligence_v12" / "routes.py",
        "sprint13_plugins": PROJECT / "services" / "plugin_platform_v13" / "routes.py",
        "dashboard": PROJECT / "dashboard" / "index.html",
        "mobile": PROJECT / "dashboard" / "mobile" / "index.html",
        "pwa": PROJECT / "dashboard" / "pwa" / "sw.js",
    }


def audit() -> dict[str, Any]:
    components = {
        name: {
            "ready": path.is_file(),
            "path": str(path.relative_to(PROJECT)),
        }
        for name, path in component_paths().items()
    }
    ready = sum(1 for item in components.values() if item["ready"])
    total = len(components)
    return {
        "status": "production" if ready == total else "incomplete",
        "ready": ready,
        "total": total,
        "components": components,
    }


def manifest() -> dict[str, Any]:
    path = PROJECT / "data" / "noorbrain_release_v14.json"
    if not path.is_file():
        return {"version": "14.0.0", "status": "missing"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": "14.0.0", "status": "invalid"}


@router.get("/health")
async def health() -> dict[str, Any]:
    result = audit()
    return {
        "status": "healthy" if result["status"] == "production" else "degraded",
        "service": "noorbrain_platform_release_v14",
        "version": "14.0.0",
        "release": manifest(),
    }


@router.get("/audit")
async def system_audit() -> dict[str, Any]:
    return {
        "version": "14.0.0",
        **audit(),
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "architecture": platform.machine(),
        },
    }


@router.get("/release")
async def release() -> dict[str, Any]:
    return {"status": "ok", "release": manifest()}
