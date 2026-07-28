from __future__ import annotations

import os
import platform
import time
from pathlib import Path
from typing import Any


class PerformanceMonitor:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.request_count = 0

    def touch(self) -> None:
        self.request_count += 1

    def snapshot(self) -> dict[str, Any]:
        project = Path(__file__).resolve().parents[2]
        data_dir = project / "data"

        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - self.started_at, 2),
            "request_count": self.request_count,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pid": os.getpid(),
            "data_files": len(list(data_dir.glob("*.json"))) if data_dir.exists() else 0,
        }


performance_monitor = PerformanceMonitor()
