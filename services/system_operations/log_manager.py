from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_ROOT = PROJECT_ROOT / "logs"
CRASH_ROOT = LOG_ROOT / "crash_reports"
ALLOWED_SUFFIXES = {".log", ".txt", ".json"}


def _safe_log_path(name: str) -> Path:
    candidate = (LOG_ROOT / name).resolve()
    root = LOG_ROOT.resolve()
    if root not in candidate.parents or candidate.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Invalid log file")
    return candidate


def list_logs() -> list[dict[str, Any]]:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in sorted(LOG_ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES:
            stat = path.stat()
            records.append({
                "name": str(path.relative_to(LOG_ROOT)),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            })
    return records


def tail_log(name: str, lines: int = 200) -> dict[str, Any]:
    lines = max(1, min(lines, 1000))
    path = _safe_log_path(name)
    if not path.exists():
        raise FileNotFoundError(name)
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"name": name, "lines": content[-lines:], "returned": min(len(content), lines)}


def create_crash_report(component: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    CRASH_ROOT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    safe_component = "".join(ch for ch in component if ch.isalnum() or ch in "-_")[:40] or "unknown"
    path = CRASH_ROOT / f"{now.strftime('%Y%m%dT%H%M%SZ')}-{safe_component}.json"
    payload = {
        "created_at": now.isoformat(),
        "component": safe_component,
        "message": message[:2000],
        "details": details or {},
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {"status": "created", "name": str(path.relative_to(LOG_ROOT))}


def rotate_logs(max_bytes: int = 5_000_000, keep: int = 5) -> dict[str, Any]:
    max_bytes = max(100_000, min(max_bytes, 100_000_000))
    keep = max(1, min(keep, 20))
    rotated: list[str] = []
    for path in LOG_ROOT.glob("*.log"):
        if path.stat().st_size < max_bytes:
            continue
        for index in range(keep, 0, -1):
            old = path.with_name(f"{path.name}.{index}")
            if index == keep and old.exists():
                old.unlink()
            previous = path if index == 1 else path.with_name(f"{path.name}.{index - 1}")
            if previous.exists():
                previous.replace(old)
        path.touch()
        rotated.append(path.name)
    return {"status": "ok", "rotated": rotated}
