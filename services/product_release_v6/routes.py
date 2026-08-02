from __future__ import annotations

import json
import os
import platform
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(
    prefix="/api/product-release-v6",
    tags=["Product Release v6"],
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
EXPORTS = ROOT / "exports"
STORE = DATA / "product_release_v6.json"

DEFAULT: dict[str, Any] = {
    "version": "6.0.0",
    "release_channel": "stable",
    "theme": "system",
    "compact_mode": False,
    "animations": True,
    "diagnostics_enabled": True,
    "last_backup": "",
}


def read_store() -> dict[str, Any]:
    STORE.parent.mkdir(parents=True, exist_ok=True)

    if not STORE.exists():
        write_store(DEFAULT.copy())
        return DEFAULT.copy()

    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    result = DEFAULT.copy()

    if isinstance(data, dict):
        result.update(data)

    return result


def write_store(data: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    temp = STORE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(STORE)


def directory_size(path: Path) -> int:
    total = 0

    if not path.exists():
        return total

    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            pass

    return total


def service_checks() -> dict[str, Any]:
    checks = {
        "main.py": ROOT / "main.py",
        "dashboard": ROOT / "dashboard",
        "data": ROOT / "data",
        "services": ROOT / "services",
        "mobile": ROOT / "dashboard" / "mobile" / "index.html",
        "sprint2": ROOT / "services" / "smart_home_v3",
        "sprint4": ROOT / "services" / "halo_ai_v4",
        "sprint5": ROOT / "services" / "islamic_center_v5",
    }

    return {
        name: {
            "present": path.exists(),
            "path": str(path.relative_to(ROOT)) if path.exists() else str(path),
        }
        for name, path in checks.items()
    }


def backup_paths() -> list[Path]:
    paths = []

    for name in (
        "data",
        "config",
        "dashboard",
        "services",
        "main.py",
        "requirements.txt",
    ):
        path = ROOT / name

        if path.exists():
            paths.append(path)

    return paths


@router.get("/health")
def health() -> dict[str, Any]:
    settings = read_store()

    return {
        "status": "healthy",
        "service": "product_release_v6",
        "version": "6.0.0",
        "channel": settings["release_channel"],
    }


@router.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    settings = read_store()

    return {
        "status": "ok",
        "release": settings,
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "pid": os.getpid(),
            "time": datetime.now().isoformat(timespec="seconds"),
        },
        "storage": {
            "data_bytes": directory_size(DATA),
            "dashboard_bytes": directory_size(ROOT / "dashboard"),
            "services_bytes": directory_size(ROOT / "services"),
            "free_bytes": shutil.disk_usage(ROOT).free,
        },
        "checks": service_checks(),
    }


@router.get("/settings")
def get_settings() -> dict[str, Any]:
    return {
        "status": "ok",
        "settings": read_store(),
    }


@router.post("/settings")
def update_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    data = read_store()

    for key in (
        "release_channel",
        "theme",
        "compact_mode",
        "animations",
        "diagnostics_enabled",
    ):
        if key in payload:
            data[key] = payload[key]

    write_store(data)

    return {
        "status": "updated",
        "settings": data,
    }


@router.post("/backup")
def create_backup() -> dict[str, Any]:
    EXPORTS.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_base = EXPORTS / f"NoorBrain-Backup-{stamp}"
    stage = EXPORTS / f".backup-stage-{stamp}"

    if stage.exists():
        shutil.rmtree(stage)

    stage.mkdir(parents=True, exist_ok=True)

    try:
        for source in backup_paths():
            target = stage / source.name

            if source.is_dir():
                shutil.copytree(
                    source,
                    target,
                    ignore=shutil.ignore_patterns(
                        "__pycache__",
                        "*.pyc",
                        "*.pyo",
                        "*.log",
                        "*.lock",
                    ),
                )
            else:
                shutil.copy2(source, target)

        archive = shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=stage,
        )
    finally:
        if stage.exists():
            shutil.rmtree(stage)

    data = read_store()
    data["last_backup"] = str(archive)
    write_store(data)

    return {
        "status": "created",
        "filename": Path(archive).name,
        "download": f"/api/product-release-v6/backups/{Path(archive).name}",
        "size_bytes": Path(archive).stat().st_size,
    }


@router.get("/backups")
def list_backups() -> dict[str, Any]:
    EXPORTS.mkdir(parents=True, exist_ok=True)

    backups = []

    for path in sorted(
        EXPORTS.glob("NoorBrain-Backup-*.zip"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        backups.append(
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "modified": datetime.fromtimestamp(
                    path.stat().st_mtime
                ).isoformat(timespec="seconds"),
                "download": f"/api/product-release-v6/backups/{path.name}",
            }
        )

    return {
        "status": "ok",
        "backups": backups,
    }


@router.get("/backups/{filename}")
def download_backup(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    path = EXPORTS / safe_name

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Backup not found.",
        )

    return FileResponse(
        path,
        filename=safe_name,
        media_type="application/zip",
    )


@router.delete("/backups/{filename}")
def delete_backup(filename: str) -> dict[str, Any]:
    safe_name = Path(filename).name
    path = EXPORTS / safe_name

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Backup not found.",
        )

    path.unlink()

    return {
        "status": "deleted",
        "filename": safe_name,
    }


@router.post("/self-check")
def self_check() -> dict[str, Any]:
    checks = service_checks()
    failed = [
        name
        for name, result in checks.items()
        if not result["present"]
    ]

    return {
        "status": "pass" if not failed else "warning",
        "failed": failed,
        "checks": checks,
        "timestamp": int(time.time()),
    }
