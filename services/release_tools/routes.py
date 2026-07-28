from __future__ import annotations
import os, shutil, subprocess, tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Body, HTTPException

router = APIRouter(prefix="/api/release-tools", tags=["Release Tools"])
PROJECT = Path(__file__).resolve().parents[2]

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "release_tools",
        "version": "3.6-c6",
        "project": str(PROJECT),
        "git": shutil.which("git") is not None,
        "disk_free_bytes": shutil.disk_usage(PROJECT).free,
    }

@router.get("/version")
def version() -> dict[str, Any]:
    commit = None
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT, text=True, timeout=5).strip()
    except Exception:
        pass
    return {"status": "ok", "version": "3.6-c6", "git_commit": commit, "generated_at": utc_now()}

@router.post("/backup")
def backup(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    backup_dir = PROJECT / "backups" / "release-tools"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"noorbrain-release-{stamp}.tar.gz"

    excludes = {"venv", ".git", "backups", "__pycache__"}
    with tarfile.open(target, "w:gz") as archive:
        for path in PROJECT.iterdir():
            if path.name in excludes:
                continue
            archive.add(path, arcname=path.name, recursive=True)

    return {"status": "created", "path": str(target), "size_bytes": target.stat().st_size}

@router.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    checks = {
        "main_py": (PROJECT / "main.py").is_file(),
        "dashboard": (PROJECT / "dashboard").is_dir(),
        "halo_os": (PROJECT / "services" / "halo_os").is_dir(),
        "voice_os": (PROJECT / "services" / "voice_os").is_dir(),
        "smart_home_runtime": (PROJECT / "services" / "smart_home_runtime").is_dir(),
        "family_ai": (PROJECT / "services" / "family_ai").is_dir(),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
