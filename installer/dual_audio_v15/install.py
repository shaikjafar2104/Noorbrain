#!/usr/bin/env python3
from __future__ import annotations
import json,re,shutil,subprocess
from datetime import datetime
from pathlib import Path

V="20260802-1";INIT='from .routes import router\n\n__all__=["router"]\n'
ROUTES=r'''from __future__ import annotations
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
'''
PI_NODE=r'''from __future__ import annotations
import base64,shutil,subprocess,tempfile
from pathlib import Path
from fastapi import APIRouter,Body,FastAPI,HTTPException
app=FastAPI(title="NoorBrain Pi Audio Node",version="15.1.0");router=APIRouter(prefix="/api/pi-audio")
def command(name):
 path=shutil.which(name)
 if not path:raise RuntimeError(f"{name} not installed")
 return path
@app.get("/health")
def health():return {"status":"healthy","service":"noorbrain_pi_audio","version":"15.1.0","arecord":bool(shutil.which("arecord")),"aplay":bool(shutil.which("aplay"))}
@app.post("/play")
def play(payload:dict=Body(...)):
 try:data=base64.b64decode(str(payload.get("audio_base64") or ""),validate=True)
 except Exception as e:raise HTTPException(422,"Invalid audio") from e
 fmt=str(payload.get("format") or "wav").lower();suffix="."+(fmt if fmt in ("wav","mp3","ogg") else "wav")
 with tempfile.NamedTemporaryFile(suffix=suffix) as f:
  f.write(data);f.flush()
  if suffix==".wav":subprocess.run([command("aplay"),"-q",f.name],check=True,timeout=120)
  else:subprocess.run([command("ffplay"),"-nodisp","-autoexit","-loglevel","quiet",f.name],check=True,timeout=120)
 return {"status":"played","bytes":len(data)}
@app.post("/record")
def record(payload:dict=Body(default={})):
 seconds=max(1,min(int(payload.get("seconds",4)),15))
 with tempfile.NamedTemporaryFile(suffix=".wav") as f:
  subprocess.run([command("arecord"),"-q","-D","default","-f","S16_LE","-r","16000","-c","1","-d",str(seconds),f.name],check=True,timeout=seconds+10)
  data=Path(f.name).read_bytes()
 return {"status":"captured","format":"wav","seconds":seconds,"audio_base64":base64.b64encode(data).decode()}
app.include_router(router)
if __name__=="__main__":
 import uvicorn;uvicorn.run(app,host="0.0.0.0",port=8010)
'''
JS=r'''(()=>{"use strict";if(window.NoorBrainDualAudio?.installed)return;const A="/api/dual-audio-v15";async function api(p,o={}){const r=await fetch(A+p,{cache:"no-store",headers:{"Content-Type":"application/json"},...o}),b=await r.json().catch(()=>({}));if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b}function panel(){let p=document.getElementById("nbDualAudioV15");if(p)return p;p=document.createElement("section");p.id="nbDualAudioV15";p.className="nb-dual-audio";p.innerHTML=`<h3>App + Raspberry Pi Audio</h3><p id="nbDaStatus">Loading…</p><label>Microphone<select id="nbDaInput"><option value="app">App</option><option value="pi">Raspberry Pi</option><option value="both">Both</option></select></label><label>Speaker<select id="nbDaOutput"><option value="app">App</option><option value="pi">Raspberry Pi</option><option value="both">Both</option></select></label><label>Pi Audio URL<input id="nbDaUrl" value="http://192.168.2.29:8010"></label><button id="nbDaSave">Save Audio Routing</button>`;const host=document.getElementById("nbVoicePlatformV9")||document.querySelector("main")||document.body;host.appendChild(p);p.querySelector("#nbDaSave").onclick=save;return p}async function load(){const p=panel();try{const d=(await api("/config")).config;p.querySelector("#nbDaInput").value=d.input_mode;p.querySelector("#nbDaOutput").value=d.output_mode;p.querySelector("#nbDaUrl").value=d.pi_node_url;p.querySelector("#nbDaStatus").textContent="Dual audio routing ready · Electronic TTS off"}catch(e){p.querySelector("#nbDaStatus").textContent=e.message}}async function save(){const p=panel();await api("/config",{method:"PATCH",body:JSON.stringify({input_mode:p.querySelector("#nbDaInput").value,output_mode:p.querySelector("#nbDaOutput").value,pi_node_url:p.querySelector("#nbDaUrl").value})});await load()}function start(){panel();load()}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();window.NoorBrainDualAudio=Object.freeze({installed:true,version:"15.1.0",load})})();
'''
CSS=r'''.nb-dual-audio{margin-top:16px;padding:16px;border:1px solid #345170;border-radius:15px;background:#17263c}.nb-dual-audio h3{margin-top:0}.nb-dual-audio p{color:#9eacc2}.nb-dual-audio label{display:flex;gap:7px;margin:12px 0;flex-direction:column}.nb-dual-audio select,.nb-dual-audio input{padding:11px;border:1px solid #38516f;border-radius:10px;color:#fff;background:#101b2d}.nb-dual-audio button{width:100%;padding:12px;border:0;border-radius:11px;background:#5aa9ff;font-weight:800}
'''
TEST=r'''import json,urllib.request
B="http://127.0.0.1:8001"
def c(p,m="GET",x=None):
 d=json.dumps(x).encode() if x is not None else None;h={"Content-Type":"application/json"} if d else {};q=urllib.request.Request(B+p,data=d,headers=h,method=m)
 with urllib.request.urlopen(q,timeout=30) as r:return json.loads(r.read().decode())
assert c("/api/dual-audio-v15/health")["version"]=="15.1.0"
x=c("/api/dual-audio-v15/config","PATCH",{"input_mode":"both","output_mode":"both","pi_node_url":"http://192.168.2.29:8010"})["config"];assert x["electronic_tts"] is False
with urllib.request.urlopen(B+"/mobile",timeout=30) as r:h=r.read().decode(errors="replace")
assert "dual-audio-v15.js?v=20260802-1" in h
print("ALL DUAL APP AND RASPBERRY PI AUDIO ROUTING TESTS PASSED")
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
 p=project();mp=p/"main.py";pages=[p/"dashboard/index.html",p/"dashboard/mobile/index.html"];sw=p/"dashboard/pwa/sw.js";b=p/"backups"/f"dual-audio-{datetime.now().strftime('%Y%m%d-%H%M%S')}";b.mkdir(parents=True)
 for x in [mp,*pages,sw]:r=x.relative_to(p);y=b/r;y.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(x,y)
 s=p/"services/dual_audio_v15";s.mkdir(parents=True,exist_ok=True);(s/"__init__.py").write_text(INIT);(s/"routes.py").write_text(ROUTES)
 tool=p/"tools/noorbrain_pi_audio_node.py";tool.parent.mkdir(parents=True,exist_ok=True);tool.write_text(PI_NODE)
 j=p/"dashboard/js/dual-audio-v15.js";c=p/"dashboard/css/dual-audio-v15.css";j.parent.mkdir(parents=True,exist_ok=True);c.parent.mkdir(parents=True,exist_ok=True);j.write_text(JS);c.write_text(CSS)
 for x in pages:inject(x,"</head>",f'<link rel="stylesheet" href="/dashboard-static/css/dual-audio-v15.css?v={V}">',r'\s*<link[^>]+dual-audio-v15\.css[^>]*>');inject(x,"</body>",f'<script src="/dashboard-static/js/dual-audio-v15.js?v={V}"></script>',r'\s*<script[^>]+dual-audio-v15\.js[^>]*></script>')
 t=mp.read_text();imp="from services.dual_audio_v15.routes import router as dual_audio_v15_router";inc="app.include_router(dual_audio_v15_router)";a=[x for x in (imp,inc) if x not in t];mp.write_text(t.rstrip()+("\n\n# DUAL AUDIO V15\n"+"\n".join(a)+"\n" if a else "\n"))
 wt=sw.read_text();wt=re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];','const CACHE = "noorbrain-dual-audio-v15";',wt,count=1);sw.write_text(wt)
 cfg=p/"data/dual_audio_v15.json";cfg.parent.mkdir(parents=True,exist_ok=True);cfg.write_text(json.dumps({"version":"15.1.0","input_mode":"both","output_mode":"both","pi_node_url":"http://192.168.2.29:8010","electronic_tts":False,"app_audio":True,"pi_audio":True},indent=2)+"\n")
 test=p/"tests/dual_audio_v15_smoke_test.py";test.write_text(TEST);ins=p/"installer/dual_audio_v15";ins.mkdir(parents=True,exist_ok=True);rollback=ins/"rollback.py";rollback.write_text("print('Use backup: "+str(b)+"')\n")
 py=p/"venv/bin/python";subprocess.run([str(py),"-m","py_compile",str(Path(__file__).resolve()),str(mp),str(s/"routes.py"),str(tool),str(test)],check=True);print("DUAL APP + PI AUDIO ROUTING INSTALLED");print("PI NODE:",tool);return 0
if __name__=="__main__":raise SystemExit(main())
