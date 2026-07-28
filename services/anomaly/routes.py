from typing import Optional
from fastapi import APIRouter, Query
from services.learning.storage import get_store
from .engine import AnomalyEngine
router=APIRouter(prefix="/api/anomaly",tags=["Sprint 9.3 Anomaly"])
def engine():return AnomalyEngine(get_store())
@router.get("/health")
def health():return {"status":"healthy","service":"anomaly","sprint":"9.3"}
@router.get("/scan")
def scan(hours:int=Query(24,ge=1,le=168),person_id:Optional[str]=None):return engine().scan(hours=hours,person_id=person_id)
@router.get("/missed-routines")
def missed(days:int=Query(14,ge=3,le=60),person_id:Optional[str]=None):return engine().missed_routines(days=days,person_id=person_id)
