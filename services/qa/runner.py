from __future__ import annotations

import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
BASE_URL = "http://127.0.0.1:8001"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    latency_ms: float | None = None


def _request(path: str, method: str = "GET", timeout: float = 5.0) -> tuple[int, bytes, float]:
    request = urllib.request.Request(BASE_URL + path, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            elapsed = (time.perf_counter() - started) * 1000
            return response.status, body, elapsed
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return exc.code, exc.read(), elapsed


def _api_check(path: str, required: bool = True) -> CheckResult:
    try:
        status, body, latency = _request(path)
        passed = 200 <= status < 300
        detail = f"HTTP {status}"
        if passed:
            try:
                json.loads(body.decode("utf-8"))
                detail += ", valid JSON"
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail += ", non-JSON response"
        return CheckResult(path, passed or not required, detail, round(latency, 2))
    except Exception as exc:
        return CheckResult(path, not required, f"{type(exc).__name__}: {exc}")


def _file_check(name: str, path: Path, minimum_bytes: int = 1) -> CheckResult:
    exists = path.is_file()
    size = path.stat().st_size if exists else 0
    return CheckResult(name, exists and size >= minimum_bytes, f"path={path}, bytes={size}")


def run_smoke_tests() -> dict[str, Any]:
    checks = [
        _api_check("/health"),
        _api_check("/api/memory/health"),
        _api_check("/api/intelligence/health", required=False),
        _api_check("/api/scene/health", required=False),
        _api_check("/api/decision/health", required=False),
        _api_check("/api/system/health", required=False),
        _api_check("/api/operations/health", required=False),
        _file_check("dashboard/index.html", PROJECT_ROOT / "dashboard" / "index.html", 32),
        _file_check("database", PROJECT_ROOT / "noorbrain.db", 1),
        _file_check("main.py", PROJECT_ROOT / "main.py", 100),
    ]
    passed = sum(item.passed for item in checks)
    result = {
        "status": "passed" if passed == len(checks) else "failed",
        "passed": passed,
        "total": len(checks),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": [asdict(item) for item in checks],
    }
    save_report(result)
    return result


def run_benchmark(samples: int = 5) -> dict[str, Any]:
    samples = max(1, min(int(samples), 25))
    latencies: list[float] = []
    errors: list[str] = []
    for _ in range(samples):
        try:
            status, _, latency = _request("/health", timeout=5.0)
            if 200 <= status < 300:
                latencies.append(latency)
            else:
                errors.append(f"HTTP {status}")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    return {
        "status": "ok" if latencies and not errors else "degraded",
        "samples_requested": samples,
        "samples_completed": len(latencies),
        "average_ms": round(statistics.mean(latencies), 2) if latencies else None,
        "minimum_ms": round(min(latencies), 2) if latencies else None,
        "maximum_ms": round(max(latencies), 2) if latencies else None,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_report(report: dict[str, Any]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    latest = REPORT_DIR / "latest.json"
    latest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return latest


def load_latest_report() -> dict[str, Any]:
    latest = REPORT_DIR / "latest.json"
    if not latest.exists():
        return {"status": "not-run", "message": "Run POST /api/qa/run first."}
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "error", "message": str(exc)}
