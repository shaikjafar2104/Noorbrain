from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.system_operations.backup_manager import create_backup, list_backups, prune_backups
from services.system_operations.log_manager import create_crash_report, list_logs, rotate_logs, tail_log
from services.system_operations.monitor import system_health
from services.system_operations.watchdog import watchdog

router = APIRouter(prefix="/api/operations", tags=["Sprint 8.5 Operations"])
_camera_client: Any = None
_vision_engine: Any = None


class BackupRequest(BaseModel):
    label: str = Field(default="manual", max_length=40)


class PruneRequest(BaseModel):
    keep: int = Field(default=14, ge=1, le=100)


class RotationRequest(BaseModel):
    max_bytes: int = Field(default=5_000_000, ge=100_000, le=100_000_000)
    keep: int = Field(default=5, ge=1, le=20)


class CrashReportRequest(BaseModel):
    component: str = Field(max_length=40)
    message: str = Field(max_length=2000)
    details: dict[str, Any] = Field(default_factory=dict)


def configure(camera_client: Any, vision_engine: Any) -> None:
    global _camera_client, _vision_engine
    _camera_client = camera_client
    _vision_engine = vision_engine


def current_health() -> dict[str, Any]:
    return system_health(_camera_client, _vision_engine)


def start_watchdog() -> None:
    watchdog.start(current_health)


def stop_watchdog() -> None:
    watchdog.stop()


@router.get("/health")
def health() -> dict[str, Any]:
    return current_health()


@router.get("/watchdog")
def watchdog_status() -> dict[str, Any]:
    return {"status": "ok", "watchdog": watchdog.snapshot()}


@router.post("/watchdog/check")
def watchdog_check() -> dict[str, Any]:
    return {"status": "ok", "watchdog": watchdog.run_once()}


@router.get("/backups")
def backups() -> dict[str, Any]:
    items = list_backups()
    return {"status": "ok", "count": len(items), "backups": items}


@router.post("/backups")
def backup(request: BackupRequest) -> dict[str, Any]:
    try:
        return create_backup(request.label)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/backups/prune")
def prune(request: PruneRequest) -> dict[str, Any]:
    return prune_backups(request.keep)


@router.get("/logs")
def logs() -> dict[str, Any]:
    items = list_logs()
    return {"status": "ok", "count": len(items), "logs": items}


@router.get("/logs/tail")
def log_tail(name: str, lines: int = Query(default=200, ge=1, le=1000)) -> dict[str, Any]:
    try:
        return tail_log(name, lines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Log file not found") from exc


@router.post("/logs/rotate")
def log_rotate(request: RotationRequest) -> dict[str, Any]:
    return rotate_logs(request.max_bytes, request.keep)


@router.post("/crash-reports")
def crash_report(request: CrashReportRequest) -> dict[str, Any]:
    return create_crash_report(request.component, request.message, request.details)
