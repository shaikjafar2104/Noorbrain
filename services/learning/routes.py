"""FastAPI routes for Sprint 9.1 Packs 1-5."""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from .dashboard import LearningDashboardBuilder
from .models import LearningEventCreate
from .patterns import DailyPatternBuilder, WeeklyPatternBuilder, MonthlyPatternBuilder
from .reports import LearningReportGenerator
from .storage import get_store

router=APIRouter(prefix="/api/learning",tags=["Sprint 9.1 Learning"])

@router.get("/health")
def learning_health():
    store=get_store(); return {"status":"healthy","service":"learning","sprint":"9.1","packs":[1,2,3,4,5],"database":str(store.db_path),"integrity":store.integrity_check()}

@router.post("/events",status_code=201)
def create_event(payload:LearningEventCreate):
    return get_store().add_event(event_type=payload.event_type,source=payload.source,room=payload.room,person_id=payload.person_id,value=payload.value,metadata=payload.metadata,occurred_at=payload.occurred_at)

@router.get("/events")
def list_events(limit:int=Query(100,ge=1,le=1000),offset:int=Query(0,ge=0),event_type:Optional[str]=None,room:Optional[str]=None,person_id:Optional[str]=None,start_at:Optional[str]=None,end_at:Optional[str]=None):
    events=get_store().list_events(limit=limit,offset=offset,event_type=event_type,room=room,person_id=person_id,start_at=start_at,end_at=end_at)
    return {"status":"ok","count":len(events),"events":events}

@router.get("/stats")
def learning_stats():
    store=get_store(); by_type=store.aggregate("SELECT event_type,COUNT(*) AS count FROM learning_events GROUP BY event_type ORDER BY count DESC,event_type LIMIT 50"); by_room=store.aggregate("SELECT COALESCE(room,'unknown') AS room,COUNT(*) AS count FROM learning_events GROUP BY COALESCE(room,'unknown') ORDER BY count DESC,room LIMIT 50")
    return {"status":"ok","total_events":store.count_events(),"by_type":by_type,"by_room":by_room}

@router.get("/patterns/daily")
def daily_pattern(day:Optional[str]=None,person_id:Optional[str]=None):
    if day:
        try: date.fromisoformat(day)
        except ValueError as exc: raise HTTPException(422,"day must be YYYY-MM-DD") from exc
    return DailyPatternBuilder(get_store()).build(day=day,person_id=person_id)

@router.get("/patterns/weekly")
def weekly_pattern(week_start:Optional[str]=None,person_id:Optional[str]=None):
    if week_start:
        try: parsed=date.fromisoformat(week_start)
        except ValueError as exc: raise HTTPException(422,"week_start must be YYYY-MM-DD") from exc
        if parsed.weekday()!=0: raise HTTPException(422,"week_start must be a Monday")
    return WeeklyPatternBuilder(get_store()).build(week_start=week_start,person_id=person_id)

@router.get("/patterns/monthly")
def monthly_pattern(month:Optional[str]=None,person_id:Optional[str]=None):
    if month:
        try: datetime.strptime(month,"%Y-%m")
        except ValueError as exc: raise HTTPException(422,"month must be YYYY-MM") from exc
    return MonthlyPatternBuilder(get_store()).build(month=month,person_id=person_id)

@router.get("/dashboard")
def learning_dashboard(person_id:Optional[str]=None): return LearningDashboardBuilder(get_store()).build(person_id=person_id)

@router.get("/report")
def learning_report(person_id:Optional[str]=None): return LearningReportGenerator(get_store()).generate(person_id=person_id)
