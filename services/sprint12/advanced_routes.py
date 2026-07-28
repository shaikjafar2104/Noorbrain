from typing import Any
from fastapi import APIRouter,Body,HTTPException
from .profiles import profile_store
from .semantic_memory import semantic_memory
from .tool_engine import tool_engine
from .action_planner import action_planner
router=APIRouter(prefix='/api/sprint12/advanced',tags=['Sprint 12 Advanced'])
@router.get('/health')
def health(): return {'status':'healthy','packs':[1,2,3],'half':1}
@router.get('/profiles')
def profiles(): return {'status':'ok','profiles':profile_store.list()}
@router.post('/profiles')
def create_profile(payload:dict[str,Any]=Body(...)):
    try:return {'status':'created','profile':profile_store.create(payload)}
    except ValueError as e: raise HTTPException(422,str(e))
@router.patch('/profiles/{profile_id}')
def update_profile(profile_id:str,payload:dict[str,Any]=Body(...)):
    try:return {'status':'updated','profile':profile_store.update(profile_id,payload)}
    except KeyError as e: raise HTTPException(404,str(e))
@router.delete('/profiles/{profile_id}')
def delete_profile(profile_id:str):
    if not profile_store.delete(profile_id): raise HTTPException(404,'Profile not found')
    return {'status':'deleted'}
@router.post('/memory/search')
def memory_search(payload:dict[str,Any]=Body(...)): return {'status':'ok','results':semantic_memory.search(str(payload.get('query') or ''),payload.get('session_id'),int(payload.get('limit',10)))}
@router.get('/memory/{session_id}/summary')
def memory_summary(session_id:str): return {'status':'ok','summary':semantic_memory.summarize(session_id)}
@router.get('/tools')
def tools(): return {'status':'ok','tools':tool_engine.list()}
@router.post('/tools/{name}/execute')
def execute_tool(name:str,payload:dict[str,Any]=Body(default={})):
    try:return {'status':'ok','result':tool_engine.execute(name,payload)}
    except KeyError as e: raise HTTPException(404,str(e))
@router.post('/actions/plan')
def plan(payload:dict[str,Any]=Body(...)): return action_planner.plan(str(payload.get('intent') or ''),payload.get('context') or {})
@router.post('/actions/execute')
def execute(payload:dict[str,Any]=Body(...)): return {'status':'ok','result':action_planner.execute(payload)}
