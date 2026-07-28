from __future__ import annotations

import time
from typing import Any

from .family_profiles import family_profiles
from .fusion import fusion_engine
from .memory_v2 import memory_v2
from .metrics import metrics
from .performance import performance_monitor
from .planner import planner
from .skills import skill_engine


class Sprint12FinalQA:
    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        checks: list[dict[str, Any]] = []

        def check(name: str, fn) -> None:
            try:
                result = fn()
                checks.append({
                    "name": name,
                    "status": "PASS" if bool(result) else "FAIL",
                    "detail": result,
                })
            except Exception as exc:
                checks.append({
                    "name": name,
                    "status": "FAIL",
                    "detail": f"{type(exc).__name__}: {exc}",
                })

        check("memory_store", lambda: isinstance(memory_v2.store.read(), list))
        check("skill_engine", lambda: len(skill_engine.list()) >= 1)
        check("planner_store", lambda: isinstance(planner.list(), list))
        check("fusion_store", lambda: isinstance(fusion_engine.store.read(), list))
        check("family_profiles", lambda: isinstance(family_profiles.list(), list))
        check("metrics", lambda: metrics.snapshot()["status"] == "ok")
        check("performance", lambda: performance_monitor.snapshot()["status"] == "ok")

        passed = sum(1 for item in checks if item["status"] == "PASS")
        failed = len(checks) - passed

        return {
            "status": "PASS" if failed == 0 else "FAIL",
            "passed": passed,
            "failed": failed,
            "checks": checks,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }


sprint12_final_qa = Sprint12FinalQA()
