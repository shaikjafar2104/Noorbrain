from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from services.learning.storage import get_store
from .engine import PredictionEngine
router=APIRouter(prefix="/api/prediction",tags=["Sprint 9.2 Prediction"])
def engine(): return PredictionEngine(get_store())
@router.get("/health")
def health(): return {"status":"healthy","service":"prediction","sprint":"9.2"}
@router.get("/next-room")
def next_room(current_room:Optional[str]=None,person_id:Optional[str]=None): return engine().next_room(current_room=current_room,person_id=person_id)
@router.get("/next-activity")
def next_activity(current_event_type:Optional[str]=None,person_id:Optional[str]=None): return engine().next_activity(current_event_type=current_event_type,person_id=person_id)
@router.get("/occupancy")
def occupancy(room:str=Query(...,min_length=1,max_length=80),at:Optional[datetime]=None,person_id:Optional[str]=None): return engine().occupancy(room=room,at=at,person_id=person_id)
@router.get("/reminder-time")
def reminder_time(event_type:str="prayer_reminder",person_id:Optional[str]=None): return engine().reminder_time(event_type=event_type,person_id=person_id)
@router.get("/summary")
def summary(person_id:Optional[str]=None): return engine().summary(person_id=person_id)
