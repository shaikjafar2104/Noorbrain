from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, HTTPException
from .store import family_intelligence_store

router=APIRouter(prefix="/api/family-intelligence-v11",tags=["Family Intelligence V11"])

@router.get("/health")
async def health()->dict[str,Any]:return {"status":"healthy","service":"family_intelligence_v11","version":"11.0.0"}

@router.get("/overview")
async def overview()->dict[str,Any]:return {"status":"ok",**await asyncio.to_thread(family_intelligence_store.overview)}

@router.post("/members")
async def add_member(payload:dict[str,Any]=Body(...))->dict[str,Any]:
 name=str(payload.get("name") or "").strip()
 if not name:raise HTTPException(422,"Member name is required.")
 payload=dict(payload);payload["name"]=name
 return {"status":"created","member":await asyncio.to_thread(family_intelligence_store.add_member,payload)}

@router.patch("/members/{member_id}")
async def update_member(member_id:str,payload:dict[str,Any]=Body(...))->dict[str,Any]:
 member=await asyncio.to_thread(family_intelligence_store.update_member,member_id,payload)
 if member is None:raise HTTPException(404,"Member not found.")
 return {"status":"updated","member":member}

@router.delete("/members/{member_id}")
async def delete_member(member_id:str)->dict[str,Any]:return {"status":"deleted","removed":await asyncio.to_thread(family_intelligence_store.delete_member,member_id)}

@router.post("/presence")
async def presence(payload:dict[str,Any]=Body(...))->dict[str,Any]:
 if not payload.get("member_id") and not payload.get("identity"):payload=dict(payload);payload["identity"]="unknown"
 return {"status":"recorded","event":await asyncio.to_thread(family_intelligence_store.record_presence,payload)}

@router.patch("/privacy")
async def privacy(payload:dict[str,Any]=Body(...))->dict[str,Any]:return {"status":"updated","privacy":await asyncio.to_thread(family_intelligence_store.update_privacy,payload)}
