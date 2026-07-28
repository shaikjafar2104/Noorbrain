from fastapi import APIRouter, Query
from .scene_engine import scene_engine

router = APIRouter(prefix="/api/scene", tags=["Sprint 8.1 Scene Intelligence"])

@router.get("/health")
def health():
    return scene_engine.health()

@router.get("/current")
def current_scene():
    return scene_engine.analyze()

@router.get("/occupancy")
def occupancy():
    scene = scene_engine.analyze()
    return {k: scene[k] for k in ("timestamp", "occupied", "person_count", "primary_zone", "zones")}

@router.get("/timeline")
def timeline(limit: int = Query(50, ge=1, le=200)):
    items = scene_engine.timeline(limit)
    return {"count": len(items), "items": items}
