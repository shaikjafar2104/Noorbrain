from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter, Body, HTTPException
from .service import family_linking_service
router=APIRouter(prefix="/api/family-linking",tags=["Family Linking"])
@router.get("/health")
async def health()->dict[str,Any]:
    s=await asyncio.to_thread(family_linking_service.list_links)
    return {"status":"healthy","service":"family_linking","version":"1.0.0","link_count":s["link_count"],"person_count":s["person_count"],"profile_count":s["profile_count"]}
@router.get("/links")
async def links()->dict[str,Any]: return await asyncio.to_thread(family_linking_service.list_links)
@router.post("/link")
async def link(payload:dict[str,Any]=Body(...))->dict[str,Any]:
    try: return await asyncio.to_thread(family_linking_service.link,person_id=str(payload["person_id"]),profile_id=str(payload["profile_id"]))
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
@router.post("/unlink/{person_id}")
async def unlink(person_id:str)->dict[str,Any]:
    try: return await asyncio.to_thread(family_linking_service.unlink,person_id)
    except KeyError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
@router.post("/auto-link")
async def auto_link()->dict[str,Any]: return await asyncio.to_thread(family_linking_service.auto_link)
