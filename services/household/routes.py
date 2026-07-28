from fastapi import APIRouter,Query
from services.learning.storage import get_store
from .engine import HouseholdEngine
router=APIRouter(prefix="/api/household",tags=["Sprint 9.4 Household"])
def engine():return HouseholdEngine(get_store())
@router.get("/health")
def health():return {"status":"healthy","service":"household","sprint":"9.4"}
@router.get("/summary")
def summary(days:int=Query(7,ge=1,le=90)):return engine().summary(days)
@router.get("/members")
def members(days:int=Query(30,ge=1,le=180)):return engine().members(days)
@router.get("/timeline")
def timeline(days:int=Query(1,ge=1,le=30),limit:int=Query(200,ge=1,le=1000)):return engine().timeline(days,limit)
@router.get("/shared-reminders")
def reminders(days:int=Query(30,ge=7,le=180)):return engine().shared_reminders(days)
