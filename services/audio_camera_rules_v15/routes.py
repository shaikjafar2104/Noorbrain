from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter,Body
router=APIRouter(prefix="/api/audio-camera-rules-v15",tags=["Unified Audio Camera Rules"])
ROOT=Path(__file__).resolve().parents[2];FILE=ROOT/"data/audio_camera_rules_v15.json"
DEFAULT={"version":"15.2.0","single_camera_mode":True,"camera_triggered_audio":True,"raspberry_pi_speaker":True,"app_speaker":True,"adhan_media_audio":True,"electronic_robotic_voice":False,"halo_natural_voice":False,"output_mode":"both"}
def read():
 if not FILE.is_file():return dict(DEFAULT)
 try:d=json.loads(FILE.read_text(encoding="utf-8"))
 except Exception:return dict(DEFAULT)
 return {**DEFAULT,**d,"single_camera_mode":True,"electronic_robotic_voice":False,"output_mode":"both"}
def write(d):FILE.parent.mkdir(parents=True,exist_ok=True);d.update({"single_camera_mode":True,"electronic_robotic_voice":False,"output_mode":"both"});FILE.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8");return d
@router.get("/health")
async def health()->dict[str,Any]:return {"status":"healthy","service":"audio_camera_rules_v15","version":"15.2.0"}
@router.get("/config")
async def config():return {"status":"ok","config":read()}
@router.patch("/config")
async def update(payload:dict=Body(...)):
 d=read()
 for key in ("camera_triggered_audio","raspberry_pi_speaker","app_speaker","adhan_media_audio","halo_natural_voice"):
  if key in payload:d[key]=bool(payload[key])
 return {"status":"updated","config":write(d)}
@router.post("/evaluate-camera-event")
async def evaluate(payload:dict=Body(default={})):
 d=read();enabled=d["camera_triggered_audio"] and bool(payload.get("rule_matched",True));targets=[]
 if enabled and d["raspberry_pi_speaker"]:targets.append("raspberry_pi")
 if enabled and d["app_speaker"]:targets.append("app")
 return {"status":"ready" if enabled else "disabled","play":enabled,"targets":targets,"media_only":True,"electronic_voice":False}
