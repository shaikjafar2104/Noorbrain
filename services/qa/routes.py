from __future__ import annotations

from fastapi import APIRouter, Query

from .runner import load_latest_report, run_benchmark, run_smoke_tests

router = APIRouter(prefix="/api/qa", tags=["QA"])


@router.get("/health")
def qa_health():
    return {"status": "healthy", "service": "qa", "version": "0.8.5-rc1"}


@router.post("/run")
def qa_run():
    return run_smoke_tests()


@router.get("/report")
def qa_report():
    return load_latest_report()


@router.get("/benchmark")
def qa_benchmark(samples: int = Query(default=5, ge=1, le=25)):
    return run_benchmark(samples)
