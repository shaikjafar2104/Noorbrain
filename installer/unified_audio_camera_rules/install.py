#!/usr/bin/env python3
from __future__ import annotations
import json,re,shutil,subprocess
from datetime import datetime
from pathlib import Path

V="20260802-1";INIT='from .routes import router\n\n__all__=["router"]\n'
ROUTES=r'''from __future__ import annotations
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
'''
JS=r'''(()=>{"use strict";if(window.NoorBrainUnifiedRules?.installed)return;const A="/api/audio-camera-rules-v15";async function api(p,o={}){const r=await fetch(A+p,{cache:"no-store",headers:{"Content-Type":"application/json"},...o}),b=await r.json().catch(()=>({}));if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b}const fields=["camera_triggered_audio","raspberry_pi_speaker","app_speaker","adhan_media_audio"];function panel(){let p=document.getElementById("nbUnifiedAudioRules");if(p)return p;p=document.createElement("section");p.id="nbUnifiedAudioRules";p.className="nb-unified-rules";p.innerHTML=`<div class="nb-ur-head"><div><small>AUDIO & CAMERA</small><h3>Reminder Playback Rules</h3><p id="nbUrStatus">Loading…</p></div><button id="nbUrSave">Save</button></div><label><input id="camera_triggered_audio" type="checkbox"> Camera-triggered recorded Dua/reminder audio</label><label><input id="raspberry_pi_speaker" type="checkbox"> Raspberry Pi speaker playback</label><label><input id="app_speaker" type="checkbox"> App audio playback</label><label><input id="adhan_media_audio" type="checkbox"> Adhan and Media Library audio</label><label class="locked"><input type="checkbox" disabled> Electronic robotic browser voice <b>OFF</b></label><label class="future"><input type="checkbox" disabled> HALO natural voice <b>Coming later</b></label>`;const host=document.getElementById("nbVoicePlatformV9")||document.querySelector("main")||document.body;host.appendChild(p);p.querySelector("#nbUrSave").onclick=save;return p}async function load(){const p=panel();try{const d=(await api("/config")).config;fields.forEach(k=>p.querySelector(`#${k}`).checked=!!d[k]);p.querySelector("#nbUrStatus").textContent="Single camera · App + Raspberry Pi"}catch(e){p.querySelector("#nbUrStatus").textContent=e.message}}async function save(){const p=panel(),data={};fields.forEach(k=>data[k]=p.querySelector(`#${k}`).checked);await api("/config",{method:"PATCH",body:JSON.stringify(data)});await load()}function removePrimary(){for(const el of document.querySelectorAll("span,b,small,button")){const t=String(el.textContent||"").trim();if(t==="Primary Camera"||/^Camera [2-6]$/.test(t))el.style.setProperty("display","none","important")}for(const h of document.querySelectorAll("h1,h2,h3,h4"))if(String(h.textContent||"").trim()==="Camera & Vision Product")h.textContent="Camera & Vision"}function start(){panel();load();removePrimary();new MutationObserver(()=>removePrimary()).observe(document.body,{childList:true,subtree:true})}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();window.NoorBrainUnifiedRules=Object.freeze({installed:true,version:"15.2.0",load})})();
'''
CSS=r'''.nb-unified-rules{margin-top:16px;padding:17px;border:1px solid #345775;border-radius:16px;background:#172940}.nb-ur-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.nb-ur-head small{color:#62b5ff;font-weight:850;letter-spacing:.12em}.nb-ur-head h3{margin:3px 0}.nb-ur-head p{margin:0;color:#9eacc2}.nb-ur-head button{padding:10px 15px;border:0;border-radius:11px;background:#5aa9ff;font-weight:800}.nb-unified-rules label{display:flex;margin:11px 0;padding:11px;border-radius:11px;align-items:center;gap:9px;background:#1e3450}.nb-unified-rules label b{margin-left:auto}.nb-unified-rules .locked{color:#ffb3aa}.nb-unified-rules .future{color:#a9b5c8}
'''
TEST=r'''import json,urllib.request
B="http://127.0.0.1:8001"
def c(p,m="GET",x=None):
 d=json.dumps(x).encode() if x is not None else None;h={"Content-Type":"application/json"} if d else {};q=urllib.request.Request(B+p,data=d,headers=h,method=m)
 with urllib.request.urlopen(q,timeout=30) as r:return json.loads(r.read().decode())
assert c("/api/audio-camera-rules-v15/health")["version"]=="15.2.0"
x=c("/api/audio-camera-rules-v15/config","PATCH",{"camera_triggered_audio":True,"raspberry_pi_speaker":True,"app_speaker":True,"adhan_media_audio":True})["config"]
assert x["single_camera_mode"] is True and x["electronic_robotic_voice"] is False and x["output_mode"]=="both"
e=c("/api/audio-camera-rules-v15/evaluate-camera-event","POST",{"rule_matched":True});assert e["targets"]==["raspberry_pi","app"] and e["electronic_voice"] is False
for p in ("/studio","/mobile"):
 with urllib.request.urlopen(B+p,timeout=30) as r:h=r.read().decode(errors="replace")
 assert "unified-audio-camera-rules.js?v=20260802-1" in h
print("ALL UNIFIED AUDIO AND CAMERA RULES TESTS PASSED")
'''
def project():
 c=Path.cwd()
 if (c/"main.py").is_file() and (c/"dashboard").is_dir():return c
 p=Path.home()/"Projects/NoorBrain"
 if p.is_dir():return p
 raise SystemExit("NoorBrain not found")
def inject(p,m,a,pat):
 t=p.read_text(encoding="utf-8",errors="replace");t=re.sub(pat,"",t,flags=re.I);i=t.lower().rfind(m);p.write_text(t[:i]+"  "+a+"\n"+t[i:],encoding="utf-8")
def main():
 p=project();mp=p/"main.py";pages=[p/"dashboard/index.html",p/"dashboard/mobile/index.html"];sw=p/"dashboard/pwa/sw.js";b=p/"backups"/f"unified-rules-{datetime.now().strftime('%Y%m%d-%H%M%S')}";b.mkdir(parents=True)
 for x in [mp,*pages,sw]:r=x.relative_to(p);y=b/r;y.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(x,y)
 s=p/"services/audio_camera_rules_v15";s.mkdir(parents=True,exist_ok=True);(s/"__init__.py").write_text(INIT);(s/"routes.py").write_text(ROUTES)
 j=p/"dashboard/js/unified-audio-camera-rules.js";c=p/"dashboard/css/unified-audio-camera-rules.css";j.parent.mkdir(parents=True,exist_ok=True);c.parent.mkdir(parents=True,exist_ok=True);j.write_text(JS);c.write_text(CSS)
 for x in pages:inject(x,"</head>",f'<link rel="stylesheet" href="/dashboard-static/css/unified-audio-camera-rules.css?v={V}">',r'\s*<link[^>]+unified-audio-camera-rules\.css[^>]*>');inject(x,"</body>",f'<script src="/dashboard-static/js/unified-audio-camera-rules.js?v={V}"></script>',r'\s*<script[^>]+unified-audio-camera-rules\.js[^>]*></script>')
 t=mp.read_text();imp="from services.audio_camera_rules_v15.routes import router as audio_camera_rules_v15_router";inc="app.include_router(audio_camera_rules_v15_router)";a=[x for x in (imp,inc) if x not in t];mp.write_text(t.rstrip()+("\n\n# UNIFIED AUDIO CAMERA RULES\n"+"\n".join(a)+"\n" if a else "\n"))
 wt=sw.read_text();wt=re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];','const CACHE = "noorbrain-unified-audio-camera-rules-v1";',wt,count=1);sw.write_text(wt)
 cfg=p/"data/audio_camera_rules_v15.json";cfg.parent.mkdir(parents=True,exist_ok=True);cfg.write_text(json.dumps({"version":"15.2.0","single_camera_mode":True,"camera_triggered_audio":True,"raspberry_pi_speaker":True,"app_speaker":True,"adhan_media_audio":True,"electronic_robotic_voice":False,"halo_natural_voice":False,"output_mode":"both"},indent=2)+"\n")
 test=p/"tests/unified_audio_camera_rules_smoke_test.py";test.write_text(TEST);py=p/"venv/bin/python";subprocess.run([str(py),"-m","py_compile",str(Path(__file__).resolve()),str(mp),str(s/"routes.py"),str(test)],check=True);print("UNIFIED AUDIO AND CAMERA RULES INSTALLED");return 0
if __name__=="__main__":raise SystemExit(main())
