from __future__ import annotations
import asyncio,base64,json,urllib.request
from pathlib import Path
from typing import Any
from fastapi import APIRouter,Body,HTTPException
router=APIRouter(prefix="/api/dual-audio-v15",tags=["Dual App Pi Audio"])
ROOT=Path(__file__).resolve().parents[2];CONFIG=ROOT/"data/dual_audio_v15.json"
DEFAULT={"version":"15.1.0","input_mode":"both","output_mode":"both","pi_node_url":"http://192.168.2.29:8010","electronic_tts":False,"app_audio":True,"pi_audio":True}
def read():
 if not CONFIG.is_file():return dict(DEFAULT)
 try:d=json.loads(CONFIG.read_text(encoding="utf-8"))
 except Exception:return dict(DEFAULT)
 return {**DEFAULT,**d,"electronic_tts":False}
def write(d):CONFIG.parent.mkdir(parents=True,exist_ok=True);d["electronic_tts"]=False;CONFIG.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8");return d
def node(path,method="GET",payload=None,timeout=20):
 c=read();data=json.dumps(payload).encode() if payload is not None else None;headers={"Content-Type":"application/json"} if data else {};req=urllib.request.Request(c["pi_node_url"].rstrip("/")+path,data=data,headers=headers,method=method)
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.loads(response.read().decode())
@router.get("/health")
async def health()->dict[str,Any]:
 c=read();pi={"status":"offline"}
 try:pi=await asyncio.to_thread(node,"/health")
 except Exception:pass
 return {"status":"healthy","service":"dual_audio_v15","version":"15.1.0","config":c,"pi":pi}
@router.get("/config")
async def config():return {"status":"ok","config":read()}
@router.patch("/config")
async def update(payload:dict=Body(...)):
 c=read()
 for key in ("input_mode","output_mode","pi_node_url","app_audio","pi_audio"):
  if key in payload:c[key]=payload[key]
 if c["input_mode"] not in ("app","pi","both"):raise HTTPException(422,"Invalid input mode")
 if c["output_mode"] not in ("app","pi","both"):raise HTTPException(422,"Invalid output mode")
 return {"status":"updated","config":write(c)}
@router.post("/play")
async def play(payload:dict=Body(...)):
 audio=str(payload.get("audio_base64") or "");fmt=str(payload.get("format") or "wav")
 if not audio:raise HTTPException(422,"Audio is required")
 try:base64.b64decode(audio,validate=True)
 except Exception as error:raise HTTPException(422,"Invalid audio") from error
 c=read();result={"app":None,"pi":None}
 if c["output_mode"] in ("app","both"):result["app"]={"audio_base64":audio,"format":fmt}
 if c["output_mode"] in ("pi","both"):
  try:result["pi"]=await asyncio.to_thread(node,"/play","POST",{"audio_base64":audio,"format":fmt},60)
  except Exception as error:result["pi"]={"status":"offline","detail":type(error).__name__}
 return {"status":"routed","output_mode":c["output_mode"],"result":result}
@router.post("/pi/record")
async def record(payload:dict=Body(default={})):
 seconds=max(1,min(int(payload.get("seconds",4)),15))
 try:return {"status":"captured","recording":await asyncio.to_thread(node,"/record","POST",{"seconds":seconds},seconds+15)}
 except Exception as error:raise HTTPException(503,f"Pi microphone unavailable: {type(error).__name__}") from error
