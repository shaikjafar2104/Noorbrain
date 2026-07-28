from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .diagnostics import automation_diagnostics
from .group_manager import group_manager
from .routine_scheduler import routine_scheduler
from .scene_manager import scene_manager

router = APIRouter(prefix="/api/automation", tags=["Automation Pack 5"])


@router.get("/diagnostics")
async def diagnostics() -> dict[str, Any]:
    return automation_diagnostics.snapshot()


@router.get("/scenes")
def list_scenes() -> dict[str, Any]:
    scenes = scene_manager.list()
    return {"status": "ok", "count": len(scenes), "scenes": scenes}


@router.post("/scenes")
def create_scene(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        scene = scene_manager.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "scene": scene}


@router.patch("/scenes/{scene_id}")
def update_scene(
    scene_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        scene = scene_manager.update(scene_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "scene": scene}


@router.delete("/scenes/{scene_id}")
def delete_scene(scene_id: str) -> dict[str, Any]:
    if not scene_manager.delete(scene_id):
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")
    return {"status": "deleted", "scene_id": scene_id}


@router.post("/scenes/{scene_id}/execute")
def execute_scene(scene_id: str) -> dict[str, Any]:
    try:
        return scene_manager.execute(scene_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/groups")
def list_groups() -> dict[str, Any]:
    groups = group_manager.list()
    return {"status": "ok", "count": len(groups), "groups": groups}


@router.post("/groups")
def create_group(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        group = group_manager.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "group": group}


@router.patch("/groups/{group_id}")
def update_group(
    group_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        group = group_manager.update(group_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "group": group}


@router.delete("/groups/{group_id}")
def delete_group(group_id: str) -> dict[str, Any]:
    if not group_manager.delete(group_id):
        raise HTTPException(status_code=404, detail=f"Group not found: {group_id}")
    return {"status": "deleted", "group_id": group_id}


@router.post("/groups/{group_id}/{action}")
def control_group(group_id: str, action: str) -> dict[str, Any]:
    if action not in {"on", "off", "toggle"}:
        raise HTTPException(status_code=422, detail="Action must be on, off, or toggle.")

    try:
        return group_manager.control(group_id, action)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/routines")
def list_routines() -> dict[str, Any]:
    routines = routine_scheduler.list()
    return {"status": "ok", "count": len(routines), "routines": routines}


@router.post("/routines")
def create_routine(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        routine = routine_scheduler.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "routine": routine}


@router.patch("/routines/{routine_id}")
def update_routine(
    routine_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        routine = routine_scheduler.update(routine_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "routine": routine}


@router.delete("/routines/{routine_id}")
def delete_routine(routine_id: str) -> dict[str, Any]:
    if not routine_scheduler.delete(routine_id):
        raise HTTPException(status_code=404, detail=f"Routine not found: {routine_id}")
    return {"status": "deleted", "routine_id": routine_id}


@router.post("/routines/{routine_id}/run")
def run_routine(routine_id: str) -> dict[str, Any]:
    try:
        return routine_scheduler.run_now(routine_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
