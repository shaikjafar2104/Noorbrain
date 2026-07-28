from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from .engine import sprint7_intelligence

router = APIRouter(prefix="/api/intelligence", tags=["Sprint 7 Intelligence"])


class ObservationPayload(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    person_id: str | int | None = None
    zone: str | None = Field(default=None, max_length=128)
    previous_zone: str | None = Field(default=None, max_length=128)
    duration: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    timestamp: float | None = None


@router.get("/health")
def health():
    return sprint7_intelligence.health()


@router.post("/observe")
def observe(payload: ObservationPayload):
    result = sprint7_intelligence.observe(payload.model_dump(), source="api")
    return {"status": "stored" if result else "ignored", "observation": result}


@router.get("/people")
def people(days: int = Query(default=30, ge=1, le=3650)):
    return sprint7_intelligence.people(days=days)


@router.get("/people/{person_id}")
def person(person_id: str, days: int = Query(default=30, ge=1, le=3650)):
    return sprint7_intelligence.person(person_id, days=days)


@router.get("/habits")
def habits(
    days: int = Query(default=30, ge=1, le=3650),
    minimum_samples: int = Query(default=2, ge=1, le=100),
):
    return sprint7_intelligence.habits(days=days, minimum_samples=minimum_samples)


@router.get("/timeline")
def timeline(
    date: str | None = None,
    person_id: str | None = None,
    zone: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
):
    return sprint7_intelligence.timeline(
        date=date, person_id=person_id, zone=zone, limit=limit
    )


@router.get("/daily-summary")
def daily_summary(date: str | None = None):
    return sprint7_intelligence.daily_summary(date=date)


@router.get("/reminder-suggestions")
def reminder_suggestions(days: int = Query(default=30, ge=1, le=3650)):
    return sprint7_intelligence.reminder_suggestions(days=days)


@router.post("/maintenance/clear")
def clear():
    return {"status": "cleared", "deleted": sprint7_intelligence.clear()}
