from __future__ import annotations

import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "noorbrain.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError):
        return {}
    return values


def _temperature_c() -> float | None:
    for candidate in (
        Path("/sys/class/thermal/thermal_zone0/temp"),
        Path("/sys/class/hwmon/hwmon0/temp1_input"),
    ):
        try:
            return round(float(candidate.read_text().strip()) / 1000.0, 1)
        except (OSError, ValueError):
            continue
    return None


def _component_snapshot(component: Any) -> dict[str, Any]:
    if component is None:
        return {"status": "unavailable"}
    snapshot: Callable[[], Any] | None = getattr(component, "snapshot", None)
    if snapshot is None:
        return {"status": "unknown"}
    try:
        value = snapshot()
        return value if isinstance(value, dict) else {"status": "ok", "value": value}
    except Exception as exc:  # health endpoint must remain available
        return {"status": "error", "error": str(exc)}


def database_health() -> dict[str, Any]:
    if not DATABASE_PATH.exists():
        return {"status": "missing", "path": str(DATABASE_PATH)}
    started = time.perf_counter()
    try:
        with sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True, timeout=2) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        check = result[0] if result else "unknown"
        return {
            "status": "healthy" if check == "ok" else "degraded",
            "quick_check": check,
            "latency_ms": elapsed_ms,
            "size_bytes": DATABASE_PATH.stat().st_size,
        }
    except (sqlite3.Error, OSError) as exc:
        return {"status": "error", "error": str(exc)}


def system_health(camera_client: Any = None, vision_engine: Any = None) -> dict[str, Any]:
    memory = _read_meminfo()
    total = memory.get("MemTotal", 0)
    available = memory.get("MemAvailable", 0)
    disk = shutil.disk_usage(PROJECT_ROOT)
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    db = database_health()
    camera = _component_snapshot(camera_client)
    vision = _component_snapshot(vision_engine)

    warnings: list[str] = []
    disk_percent = round((disk.used / disk.total) * 100, 1) if disk.total else 0.0
    memory_percent = round(((total - available) / total) * 100, 1) if total else 0.0
    temperature = _temperature_c()
    if disk_percent >= 90:
        warnings.append("disk_usage_high")
    if memory_percent >= 90:
        warnings.append("memory_usage_high")
    if temperature is not None and temperature >= 80:
        warnings.append("temperature_high")
    if db.get("status") not in {"healthy"}:
        warnings.append("database_not_healthy")

    return {
        "status": "healthy" if not warnings else "degraded",
        "checked_at": _utc_now(),
        "system": {
            "load_average": {"1m": load[0], "5m": load[1], "15m": load[2]},
            "memory": {
                "total_bytes": total,
                "available_bytes": available,
                "used_percent": memory_percent,
            },
            "disk": {
                "total_bytes": disk.total,
                "free_bytes": disk.free,
                "used_percent": disk_percent,
            },
            "temperature_c": temperature,
        },
        "components": {"camera": camera, "vision": vision, "database": db},
        "warnings": warnings,
    }
