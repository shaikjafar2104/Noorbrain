from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, Query
from .adapter import vision_snapshot
from .store import vision_event_store

router=APIRouter(prefix='/api/vision-intelligence',tags=['Vision Intelligence'])

@router.get('/health')
async def health()->dict[str,Any]:
    snap=await asyncio.to_thread(vision_snapshot)
    return {'service':'vision_intelligence','version':'3.7-d1.1','status':'healthy' if snap['status']=='healthy' else 'degraded','vision_engine':snap['status'],'person_count':snap['person_count'],'fps':snap.get('fps'),'event_store':vision_event_store.summary()}

@router.get('/snapshot')
async def snapshot()->dict[str,Any]:
    snap=await asyncio.to_thread(vision_snapshot)
    event=await asyncio.to_thread(vision_event_store.add,{'event_type':'vision_snapshot','source':'vision_engine','zone':None,'person_id':None,'confidence':None,'message':f"{snap['person_count']} person(s) currently detected.",'snapshot_path':None,'metadata':{'person_count':snap['person_count'],'fps':snap.get('fps'),'zones':snap.get('zones',[])}})
    return {'status':'ok','snapshot':snap,'event':event}

@router.post('/events')
async def create_event(payload:dict[str,Any]=Body(...))->dict[str,Any]:
    item=await asyncio.to_thread(vision_event_store.add,payload); return {'status':'created','event':item}

@router.get('/events')
async def events(limit:int=Query(100,ge=1,le=1000),event_type:str|None=None,zone:str|None=None)->dict[str,Any]:
    items=await asyncio.to_thread(vision_event_store.list,limit,event_type,zone); return {'status':'ok','count':len(items),'events':items}

@router.get('/summary')
async def summary()->dict[str,Any]: return await asyncio.to_thread(vision_event_store.summary)

@router.post('/events/clear')
async def clear_events()->dict[str,Any]: return {'status':'cleared','removed':await asyncio.to_thread(vision_event_store.clear)}
