from __future__ import annotations

from fastapi import APIRouter

from .manager import checklist, release_status, release_summary

router = APIRouter(prefix="/api/release", tags=["Release"])


@router.get("/status")
def status():
    return release_status()


@router.get("/checklist")
def get_checklist():
    return {"status": "ok", "items": checklist()}


@router.get("/summary")
def summary():
    return release_summary()
