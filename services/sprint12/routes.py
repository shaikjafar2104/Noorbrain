from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .fusion import fusion_engine
from .memory_v2 import memory_v2
from .metrics import metrics
from .planner import planner
from .skills import skill_engine

router = APIRouter(prefix="/api/sprint12", tags=["Sprint 12"])


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "sprint12",
        "packs": [1, 2, 3, 4, 5],
    }


@router.post("/memory/messages")
def add_memory(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        item = memory_v2.add(
            str(payload.get("session_id") or "default"),
            str(payload.get("role") or "user"),
            str(payload.get("content") or ""),
            dict(payload.get("metadata") or {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "message": item}


@router.get("/memory/{session_id}")
def memory_history(session_id: str, limit: int = 50) -> dict[str, Any]:
    items = memory_v2.history(session_id, limit)
    return {"status": "ok", "count": len(items), "messages": items}


@router.get("/memory/sessions/list")
def memory_sessions() -> dict[str, Any]:
    items = memory_v2.sessions()
    return {"status": "ok", "count": len(items), "sessions": items}


@router.delete("/memory/{session_id}")
def clear_memory(session_id: str) -> dict[str, Any]:
    return {"status": "deleted", "removed": memory_v2.clear(session_id)}


@router.get("/skills")
def list_skills() -> dict[str, Any]:
    items = skill_engine.list()
    return {"status": "ok", "count": len(items), "skills": items}


@router.post("/skills/{skill_name}/execute")
def execute_skill(
    skill_name: str,
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    try:
        result = skill_engine.execute(skill_name, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "skill": skill_name, "result": result}


@router.post("/planner")
def create_plan(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        plan = planner.create(
            str(payload.get("goal") or ""),
            dict(payload.get("context") or {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "plan": plan}


@router.get("/planner")
def list_plans() -> dict[str, Any]:
    items = planner.list()
    return {"status": "ok", "count": len(items), "plans": items}


@router.post("/planner/{plan_id}/approve")
def approve_plan(plan_id: str) -> dict[str, Any]:
    try:
        plan = planner.approve(plan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "approved", "plan": plan}


@router.post("/fusion")
def fuse_context(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    item = fusion_engine.fuse(
        payload.get("vision"),
        payload.get("voice"),
        payload.get("automation"),
    )
    return {"status": "ok", "event": item}


@router.get("/fusion")
def recent_fusion(limit: int = 50) -> dict[str, Any]:
    items = fusion_engine.recent(limit)
    return {"status": "ok", "count": len(items), "events": items}


@router.get("/metrics")
def sprint12_metrics() -> dict[str, Any]:
    return metrics.snapshot()


@router.get("/completion")
def completion() -> dict[str, Any]:
    snapshot = metrics.snapshot()
    return {
        "status": "complete",
        "sprint": "12",
        "ready_for_v1": True,
        "metrics": snapshot,
    }
