from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter,Body,HTTPException
from .store import store
router=APIRouter(prefix="/api/islamic-intelligence-v12",tags=["Islamic Intelligence V12"])
@router.get("/health")
async def health()->dict[str,Any]:return {"status":"healthy","service":"islamic_intelligence_v12","version":"12.0.0"}
@router.get("/overview")
async def overview():return {"status":"ok",**await asyncio.to_thread(store.overview)}
@router.post("/rules")
async def add(payload:dict=Body(...)):
 if not str(payload.get("name") or "").strip() or not str(payload.get("message") or "").strip():raise HTTPException(422,"Name and message are required.")
 return {"status":"created","rule":await asyncio.to_thread(store.add_rule,payload)}
@router.patch("/rules/{rule_id}")
async def patch(rule_id:str,payload:dict=Body(...)):
 r=await asyncio.to_thread(store.patch_rule,rule_id,payload)
 if r is None:raise HTTPException(404,"Rule not found.")
 return {"status":"updated","rule":r}
@router.delete("/rules/{rule_id}")
async def delete(rule_id:str):return {"status":"deleted","removed":await asyncio.to_thread(store.delete_rule,rule_id)}
@router.post("/evaluate")
async def evaluate(payload:dict=Body(...)):return {"status":"evaluated",**await asyncio.to_thread(store.evaluate,payload)}
@router.patch("/settings")
async def settings(payload:dict=Body(...)):return {"status":"updated","settings":await asyncio.to_thread(store.settings,payload)}
