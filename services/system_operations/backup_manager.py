from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKUP_ROOT = PROJECT_ROOT / "backups" / "operations"
DATABASE_PATH = PROJECT_ROOT / "noorbrain.db"
INCLUDE_PATHS = ("config", "dashboard", "services", "shared", "main.py", "requirements.txt")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _copy_database(destination: Path) -> None:
    if not DATABASE_PATH.exists():
        return
    with sqlite3.connect(str(DATABASE_PATH), timeout=10) as source:
        with sqlite3.connect(str(destination), timeout=10) as target:
            source.backup(target)


def create_backup(label: str = "manual") -> dict[str, Any]:
    safe_label = "".join(ch for ch in label if ch.isalnum() or ch in "-_ ").strip().replace(" ", "-")[:40] or "manual"
    destination = BACKUP_ROOT / f"{_stamp()}-{safe_label}"
    destination.mkdir(parents=True, exist_ok=False)

    copied: list[str] = []
    for relative in INCLUDE_PATHS:
        source = PROJECT_ROOT / relative
        if not source.exists():
            continue
        target = destination / relative
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        copied.append(relative)

    db_target = destination / "noorbrain.db"
    _copy_database(db_target)
    if db_target.exists():
        copied.append("noorbrain.db")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": safe_label,
        "project_root": str(PROJECT_ROOT),
        "files": copied,
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"status": "created", "backup": destination.name, "path": str(destination), "files": copied}


def list_backups() -> list[dict[str, Any]]:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for path in sorted(BACKUP_ROOT.iterdir(), reverse=True):
        if not path.is_dir():
            continue
        manifest_path = path / "manifest.json"
        manifest: dict[str, Any] = {}
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        results.append({
            "name": path.name,
            "created_at": manifest.get("created_at"),
            "label": manifest.get("label"),
            "size_bytes": sum(item.stat().st_size for item in path.rglob("*") if item.is_file()),
        })
    return results


def prune_backups(keep: int = 14) -> dict[str, Any]:
    keep = max(1, min(keep, 100))
    backups = [path for path in sorted(BACKUP_ROOT.glob("*"), reverse=True) if path.is_dir()]
    removed: list[str] = []
    for path in backups[keep:]:
        shutil.rmtree(path)
        removed.append(path.name)
    return {"status": "ok", "kept": min(len(backups), keep), "removed": removed}
