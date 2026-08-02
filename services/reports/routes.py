"""FastAPI endpoints for Sprint 9.5 complete AI Reports."""
from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from services.learning.storage import get_store
from .dashboard_adapter import DashboardAdapter
from .export_engine import ExportEngine, ExportError
from .report_engine import ReportEngine
from .storage import get_report_store

router = APIRouter(prefix="/api/reports", tags=["Sprint 9.5 AI Reports"])
ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ExportEngine(ROOT / "data" / "report_exports")


def engine() -> ReportEngine:
    return ReportEngine(get_store())


def persist(report: dict, save: bool) -> dict:
    if save:
        report["snapshot_id"] = get_report_store().save(report)
    return report


def build_report(report_type: str, day: Optional[str], week_start: Optional[str], month: Optional[str], person_id: Optional[str], days: int) -> dict:
    report_type = report_type.lower().strip()
    report_engine = engine()
    if report_type == "daily": return report_engine.daily(day, person_id)
    if report_type == "weekly": return report_engine.weekly(week_start, person_id)
    if report_type == "monthly": return report_engine.monthly(month, person_id)
    if report_type == "person":
        if not person_id: raise HTTPException(422, "person_id is required for person reports")
        return report_engine.person(person_id, days)
    if report_type == "household": return report_engine.household(days)
    if report_type == "insights": return report_engine.insight_summary(days, person_id)
    raise HTTPException(422, "report_type must be daily, weekly, monthly, person, household, or insights")


@router.get("/health")
def health():
    learning = get_store(); reports = get_report_store()
    return {
        "status": "healthy", "service": "reports", "sprint": "9.5", "half": 2,
        "complete": True,
        "features": ["daily", "weekly", "monthly", "person", "household", "insights", "json", "html", "csv", "markdown", "pdf", "dashboard", "archive"],
        "learning_integrity": learning.integrity_check(), "report_integrity": reports.integrity_check(),
    }


@router.get("/daily")
def daily(day: Optional[str] = None, person_id: Optional[str] = None, save: bool = False):
    if day:
        try: date.fromisoformat(day)
        except ValueError as exc: raise HTTPException(422, "day must be YYYY-MM-DD") from exc
    return persist(engine().daily(day, person_id), save)


@router.get("/weekly")
def weekly(week_start: Optional[str] = None, person_id: Optional[str] = None, save: bool = False):
    if week_start:
        try: date.fromisoformat(week_start)
        except ValueError as exc: raise HTTPException(422, "week_start must be YYYY-MM-DD") from exc
    return persist(engine().weekly(week_start, person_id), save)


@router.get("/monthly")
def monthly(month: Optional[str] = None, person_id: Optional[str] = None, save: bool = False):
    if month:
        try: datetime.strptime(month, "%Y-%m")
        except ValueError as exc: raise HTTPException(422, "month must be YYYY-MM") from exc
    return persist(engine().monthly(month, person_id), save)


@router.get("/person")
def person(person_id: str = Query(..., min_length=1, max_length=128), days: int = Query(30, ge=1, le=365), save: bool = False):
    return persist(engine().person(person_id, days), save)


@router.get("/household")
def household(days: int = Query(7, ge=1, le=365), save: bool = False):
    return persist(engine().household(days), save)


@router.get("/insights")
def insights(days: int = Query(30, ge=1, le=365), person_id: Optional[str] = None):
    return engine().insight_summary(days, person_id)


@router.get("/snapshots")
def snapshots(report_type: Optional[str] = None, limit: int = Query(20, ge=1, le=100)):
    rows = get_report_store().latest(report_type, limit)
    return {"status": "ok", "count": len(rows), "snapshots": rows}


@router.get("/dashboard")
def dashboard(report_type: str = "weekly", person_id: Optional[str] = None, days: int = Query(30, ge=1, le=365)):
    report = build_report(report_type, None, None, None, person_id, days)
    return DashboardAdapter.build(report)


@router.get("/export/{fmt}")
def export_report(
    fmt: str,
    report_type: str = "weekly",
    day: Optional[str] = None,
    week_start: Optional[str] = None,
    month: Optional[str] = None,
    person_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    filename: Optional[str] = Query(None, max_length=100),
    download: bool = False,
):
    report = build_report(report_type, day, week_start, month, person_id, days)
    try:
        result = EXPORTS.export(report, fmt, filename)
    except ExportError as exc:
        raise HTTPException(422, str(exc)) from exc
    if download:
        path = Path(result["path"])
        media = {"json":"application/json", "html":"text/html", "csv":"text/csv", "markdown":"text/markdown", "pdf":"application/pdf"}.get(fmt.lower(), "application/octet-stream")
        return FileResponse(path, media_type=media, filename=path.name)
    result["download_url"] = f"/api/reports/download/{result['filename']}"
    return result


@router.get("/exports")
def exports(limit: int = Query(50, ge=1, le=200)):
    rows = EXPORTS.list_exports(limit)
    return {"status": "ok", "count": len(rows), "exports": rows}


@router.get("/download/{filename}")
def download(filename: str):
    try: path = EXPORTS.resolve_export(filename)
    except ExportError as exc: raise HTTPException(422, str(exc)) from exc
    except FileNotFoundError as exc: raise HTTPException(404, "Export not found") from exc
    media = {".json":"application/json", ".html":"text/html", ".csv":"text/csv", ".md":"text/markdown", ".pdf":"application/pdf"}.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media, filename=path.name)
