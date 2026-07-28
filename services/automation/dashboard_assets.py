from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
router = APIRouter(tags=["Devices Dashboard Assets"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_ROOT = PROJECT_ROOT / "dashboard"
def serve_file(relative_path: str, media_type: str) -> FileResponse:
    target=(DASHBOARD_ROOT/relative_path).resolve(); root=DASHBOARD_ROOT.resolve()
    if root not in target.parents: raise HTTPException(status_code=403, detail="Invalid asset path.")
    if not target.is_file(): raise HTTPException(status_code=404, detail=f"Dashboard asset not found: {relative_path}")
    return FileResponse(path=target, media_type=media_type, headers={"Cache-Control":"no-cache, no-store, must-revalidate"})
@router.get("/dashboard/js/devices-dashboard.js")
def js1(): return serve_file("js/devices-dashboard.js","application/javascript")
@router.get("/dashboard/css/devices-dashboard.css")
def css1(): return serve_file("css/devices-dashboard.css","text/css")
@router.get("/dashboard/js/devices-dashboard-controls.js")
def js2(): return serve_file("js/devices-dashboard-controls.js","application/javascript")
@router.get("/dashboard/css/devices-dashboard-controls.css")
def css2(): return serve_file("css/devices-dashboard-controls.css","text/css")
