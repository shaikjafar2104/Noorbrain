"""
============================================================
Project : NoorBrain
Module  : Dashboard API Routes
Sprint  : 4.5
Purpose :
    Expose the centralized NoorBrain dashboard snapshot.
============================================================
"""

from fastapi import APIRouter

from services.dashboard import dashboard


router = APIRouter(
    tags=["Dashboard"]
)


@router.get("/dashboard")
def get_dashboard():
    return dashboard.snapshot()
