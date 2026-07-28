from __future__ import annotations
from pathlib import Path
from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/api/mobile-companion", tags=["Mobile Companion"])
PROJECT = Path(__file__).resolve().parents[2]

@router.get("/health")
def health() -> dict[str, Any]:
    pwa = PROJECT / "dashboard" / "pwa"
    mobile = PROJECT / "dashboard" / "mobile"
    checks = {
        "manifest": (pwa / "manifest.webmanifest").is_file(),
        "service_worker": (pwa / "sw.js").is_file(),
        "icon_192": (pwa / "icons" / "icon-192.png").is_file(),
        "icon_512": (pwa / "icons" / "icon-512.png").is_file(),
        "mobile_shell": (mobile / "index.html").is_file(),
    }
    return {"status": "healthy" if all(checks.values()) else "degraded", "service": "mobile_companion", "version": "3.4-c4-production", "checks": checks}

@router.get("/installability")
def installability() -> dict[str, Any]:
    item = health()
    return {"status": "PASS" if item["status"] == "healthy" else "FAIL", "requirements": {"manifest": item["checks"]["manifest"], "service_worker": item["checks"]["service_worker"], "icons": item["checks"]["icon_192"] and item["checks"]["icon_512"], "standalone_display": True, "mobile_shell": item["checks"]["mobile_shell"]}, "note": "HTTPS is required by most phone browsers for full PWA installation."}

@router.get("/links")
def links() -> dict[str, Any]:
    return {"status": "ok", "studio": "/studio", "mobile": "/mobile", "manifest": "/dashboard-pwa/manifest.webmanifest"}
