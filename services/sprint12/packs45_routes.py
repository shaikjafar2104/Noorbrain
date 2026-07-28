from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .family_profiles import family_profiles
from .final_qa import sprint12_final_qa
from .performance import performance_monitor
from .permissions import permission_engine
from .release import sprint12_release

router = APIRouter(prefix="/api/sprint12/packs45", tags=["Sprint 12 Packs 4-5"])


@router.get("/health")
def health() -> dict[str, Any]:
    performance_monitor.touch()
    return {
        "status": "healthy",
        "packs": [4, 5],
    }


@router.get("/members")
def list_members() -> dict[str, Any]:
    performance_monitor.touch()
    items = family_profiles.list()
    return {"status": "ok", "count": len(items), "members": items}


@router.post("/members")
def create_member(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    performance_monitor.touch()
    try:
        member = family_profiles.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "member": member}


@router.patch("/members/{member_id}")
def update_member(
    member_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    performance_monitor.touch()
    try:
        member = family_profiles.update(member_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "member": member}


@router.delete("/members/{member_id}")
def delete_member(member_id: str) -> dict[str, Any]:
    performance_monitor.touch()
    if not family_profiles.delete(member_id):
        raise HTTPException(status_code=404, detail=f"Member not found: {member_id}")
    return {"status": "deleted", "member_id": member_id}


@router.post("/members/{member_id}/presence")
def update_presence(
    member_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    performance_monitor.touch()
    try:
        member = family_profiles.update_presence(
            member_id,
            str(payload.get("status") or "unknown"),
            payload.get("room"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "member": member}


@router.get("/members/{member_id}/permissions/{permission}")
def permission_check(member_id: str, permission: str) -> dict[str, Any]:
    performance_monitor.touch()
    try:
        return permission_engine.explain(member_id, permission)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/performance")
def performance() -> dict[str, Any]:
    performance_monitor.touch()
    return performance_monitor.snapshot()


@router.post("/qa/run")
def run_qa() -> dict[str, Any]:
    performance_monitor.touch()
    return sprint12_final_qa.run()


@router.get("/qa/report")
def qa_report() -> dict[str, Any]:
    performance_monitor.touch()
    return sprint12_final_qa.run()


@router.get("/release")
def release_status() -> dict[str, Any]:
    performance_monitor.touch()
    return sprint12_release.status()


@router.post("/release/mark")
def mark_release() -> dict[str, Any]:
    performance_monitor.touch()
    return sprint12_release.mark()
