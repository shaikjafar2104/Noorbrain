from __future__ import annotations
import asyncio
from fastapi import APIRouter,Body,HTTPException
from .store import registry
router=APIRouter(prefix="/api/plugin-platform-v13",tags=["Plugin Platform V13"])
@router.get("/health")
async def health():return {"status":"healthy","service":"plugin_platform_v13","version":"13.0.0","execution":"manifest-safe"}
@router.get("/overview")
async def overview():return {"status":"ok",**await asyncio.to_thread(registry.overview)}
@router.post("/plugins")
async def install(payload:dict=Body(...)):
 try:p=await asyncio.to_thread(registry.install,payload)
 except ValueError as e:raise HTTPException(422,str(e)) from e
 return {"status":"installed","plugin":p}
@router.post("/plugins/{plugin_id}/enable")
async def enable(plugin_id:str,payload:dict=Body(default={})):
 p=await asyncio.to_thread(registry.enable,plugin_id,bool(payload.get("enabled",True)))
 if p is None:raise HTTPException(404,"Plugin not found.")
 return {"status":"updated","plugin":p}
@router.delete("/plugins/{plugin_id}")
async def delete(plugin_id:str):return {"status":"deleted","removed":await asyncio.to_thread(registry.delete,plugin_id)}
