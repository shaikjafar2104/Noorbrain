from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, HTTPException
from .store import whole_home_store

router=APIRouter(prefix="/api/whole-home-v10",tags=["Whole Home V10"])

@router.get("/health")
async def health()->dict[str,Any]:return {"status":"healthy","service":"whole_home_v10","version":"10.0.0"}

@router.get("/overview")
async def overview()->dict[str,Any]:return {"status":"ok",**await asyncio.to_thread(whole_home_store.overview)}

@router.post("/rooms")
async def add_room(payload:dict[str,Any]=Body(...))->dict[str,Any]:
    name=str(payload.get("name") or "").strip()
    if not name:raise HTTPException(422,"Room name is required.")
    return {"status":"created","room":await asyncio.to_thread(whole_home_store.add_room,name,str(payload.get("icon") or "🏠"))}

@router.post("/devices")
async def add_device(payload:dict[str,Any]=Body(...))->dict[str,Any]:
    if not str(payload.get("name") or "").strip():raise HTTPException(422,"Device name is required.")
    payload=dict(payload);payload["name"]=str(payload["name"]).strip()
    return {"status":"created","device":await asyncio.to_thread(whole_home_store.add_device,payload)}

@router.patch("/devices/{device_id}")
async def set_device(device_id:str,payload:dict[str,Any]=Body(...))->dict[str,Any]:
    device=await asyncio.to_thread(whole_home_store.set_device,device_id,payload)
    if device is None:raise HTTPException(404,"Device not found.")
    return {"status":"updated","device":device}

@router.delete("/devices/{device_id}")
async def delete_device(device_id:str)->dict[str,Any]:return {"status":"deleted","removed":await asyncio.to_thread(whole_home_store.delete_device,device_id)}

@router.post("/scenes")
async def add_scene(payload:dict[str,Any]=Body(...))->dict[str,Any]:
    name=str(payload.get("name") or "").strip()
    if not name:raise HTTPException(422,"Scene name is required.")
    return {"status":"created","scene":await asyncio.to_thread(whole_home_store.add_scene,name,list(payload.get("actions") or []))}

@router.post("/scenes/{scene_id}/run")
async def run_scene(scene_id:str)->dict[str,Any]:
    run=await asyncio.to_thread(whole_home_store.run_scene,scene_id)
    if run is None:raise HTTPException(404,"Scene not found.")
    return {"status":"completed","run":run}

@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id:str)->dict[str,Any]:return {"status":"deleted","removed":await asyncio.to_thread(whole_home_store.delete_scene,scene_id)}

@router.post("/automations")
async def add_automation(payload:dict[str,Any]=Body(...))->dict[str,Any]:
    if not str(payload.get("name") or "").strip():raise HTTPException(422,"Automation name is required.")
    return {"status":"created","automation":await asyncio.to_thread(whole_home_store.add_automation,payload)}

@router.post("/automations/{automation_id}/run")
async def run_automation(automation_id:str)->dict[str,Any]:
    run=await asyncio.to_thread(whole_home_store.run_automation,automation_id)
    if run is None:raise HTTPException(404,"Enabled automation not found.")
    return {"status":"completed","run":run}

@router.delete("/automations/{automation_id}")
async def delete_automation(automation_id:str)->dict[str,Any]:return {"status":"deleted","removed":await asyncio.to_thread(whole_home_store.delete_automation,automation_id)}
