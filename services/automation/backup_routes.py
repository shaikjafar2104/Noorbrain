from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from .backup_restore import automation_backup_manager

router = APIRouter(prefix="/api/automation/backups", tags=["Automation Backups"])


@router.get("/health")
def backup_health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "validation": automation_backup_manager.validate_current(),
        "backup_count": len(automation_backup_manager.list_backups()),
    }


@router.get("")
def list_backups() -> dict[str, Any]:
    items = automation_backup_manager.list_backups()
    return {"status": "ok", "count": len(items), "backups": items}


@router.post("")
def create_backup(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    try:
        return automation_backup_manager.create_backup(payload.get("label"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{backup_name}/inspect")
def inspect_backup(backup_name: str) -> dict[str, Any]:
    try:
        return automation_backup_manager.inspect_backup(backup_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Backup not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{backup_name}/download")
def download_backup(backup_name: str) -> FileResponse:
    try:
        path = automation_backup_manager.get_backup_path(backup_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Backup not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return FileResponse(
        path,
        filename=path.name,
        media_type="application/zip",
    )


@router.post("/{backup_name}/restore")
def restore_backup(
    backup_name: str,
    payload: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    try:
        return automation_backup_manager.restore_backup(
            backup_name,
            create_safety_backup=bool(payload.get("create_safety_backup", True)),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Backup not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/export/configuration")
def export_configuration(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    return automation_backup_manager.export_configuration(payload.get("label"))


@router.post("/import/configuration")
def import_configuration(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return automation_backup_manager.import_configuration(
            payload,
            create_safety_backup=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/validation/current")
def validate_current() -> dict[str, Any]:
    return automation_backup_manager.validate_current()
