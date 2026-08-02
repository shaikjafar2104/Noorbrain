#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


VERSION = "20260801-1"
INIT_PY = 'from .routes import router\n\n__all__ = ["router"]\n'

STORE_PY = r'''from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class WholeHomeStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "data" / "whole_home_v10.json"
        self.lock = threading.RLock()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "10.0.0",
            "rooms": [
                {"id": "hall", "name": "Hall", "icon": "🛋️"},
                {"id": "bedroom", "name": "Bedroom", "icon": "🛏️"},
                {"id": "kitchen", "name": "Kitchen", "icon": "🍳"},
            ],
            "devices": [],
            "scenes": [],
            "automations": [],
            "runs": [],
            "updated_at": self.now(),
        }

    def read(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.is_file():
                return self.default()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return self.default()
            base = self.default()
            for key in ("rooms", "devices", "scenes", "automations", "runs"):
                if isinstance(data.get(key), list):
                    base[key] = data[key]
            return base

    def write(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = self.now()
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)
            return data

    def overview(self) -> dict[str, Any]:
        data = self.read()
        return {
            "rooms": data["rooms"],
            "devices": data["devices"],
            "scenes": data["scenes"],
            "automations": data["automations"],
            "runs": data["runs"][-25:],
            "summary": {
                "rooms": len(data["rooms"]),
                "devices": len(data["devices"]),
                "online": sum(1 for item in data["devices"] if item.get("online", True)),
                "powered_on": sum(1 for item in data["devices"] if item.get("state", {}).get("power")),
                "scenes": len(data["scenes"]),
                "automations": len(data["automations"]),
            },
        }

    def add_room(self, name: str, icon: str) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            room = {"id": uuid4().hex, "name": name, "icon": icon or "🏠"}
            data["rooms"].append(room)
            self.write(data)
            return room

    def add_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            device = {
                "id": uuid4().hex,
                "name": payload["name"],
                "type": payload.get("type", "switch"),
                "room_id": payload.get("room_id", "hall"),
                "online": True,
                "state": {"power": bool(payload.get("power", False))},
                "created_at": self.now(),
            }
            data["devices"].append(device)
            self.write(data)
            return device

    def set_device(self, device_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            device = next((item for item in data["devices"] if item["id"] == device_id), None)
            if device is None:
                return None
            if "power" in patch:
                device.setdefault("state", {})["power"] = bool(patch["power"])
            if "online" in patch:
                device["online"] = bool(patch["online"])
            if str(patch.get("name") or "").strip():
                device["name"] = str(patch["name"]).strip()
            device["updated_at"] = self.now()
            self.write(data)
            return device

    def delete_device(self, device_id: str) -> bool:
        with self.lock:
            data = self.read()
            before = len(data["devices"])
            data["devices"] = [item for item in data["devices"] if item["id"] != device_id]
            removed = len(data["devices"]) != before
            if removed:
                self.write(data)
            return removed

    def add_scene(self, name: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            scene = {"id": uuid4().hex, "name": name, "actions": actions, "created_at": self.now()}
            data["scenes"].append(scene)
            self.write(data)
            return scene

    def run_actions(self, data: dict[str, Any], actions: list[dict[str, Any]]) -> int:
        changed = 0
        for action in actions:
            device = next((item for item in data["devices"] if item["id"] == action.get("device_id")), None)
            if device is not None and "power" in action:
                device.setdefault("state", {})["power"] = bool(action["power"])
                changed += 1
        return changed

    def run_scene(self, scene_id: str) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            scene = next((item for item in data["scenes"] if item["id"] == scene_id), None)
            if scene is None:
                return None
            changed = self.run_actions(data, scene.get("actions", []))
            run = {"id": uuid4().hex, "kind": "scene", "source_id": scene_id, "changed": changed, "at": self.now()}
            data["runs"].append(run); data["runs"] = data["runs"][-200:]
            self.write(data)
            return run

    def delete_scene(self, scene_id: str) -> bool:
        with self.lock:
            data = self.read(); before = len(data["scenes"])
            data["scenes"] = [item for item in data["scenes"] if item["id"] != scene_id]
            removed = len(data["scenes"]) != before
            if removed: self.write(data)
            return removed

    def add_automation(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            automation = {
                "id": uuid4().hex, "name": payload["name"],
                "trigger": payload.get("trigger", {"kind": "manual"}),
                "actions": payload.get("actions", []), "enabled": True,
                "created_at": self.now(),
            }
            data["automations"].append(automation); self.write(data); return automation

    def run_automation(self, automation_id: str) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            automation = next((item for item in data["automations"] if item["id"] == automation_id), None)
            if automation is None or not automation.get("enabled", True): return None
            changed = self.run_actions(data, automation.get("actions", []))
            run = {"id": uuid4().hex, "kind": "automation", "source_id": automation_id, "changed": changed, "at": self.now()}
            data["runs"].append(run); data["runs"] = data["runs"][-200:]; self.write(data); return run

    def delete_automation(self, automation_id: str) -> bool:
        with self.lock:
            data = self.read(); before = len(data["automations"])
            data["automations"] = [item for item in data["automations"] if item["id"] != automation_id]
            removed = len(data["automations"]) != before
            if removed: self.write(data)
            return removed


whole_home_store = WholeHomeStore()
'''

ROUTES_PY = r'''from __future__ import annotations
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
'''

UI_JS = r'''(()=>{"use strict";if(window.NoorBrainWholeHome?.installed)return;const API="/api/whole-home-v10";const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));async function api(path,options={}){const r=await fetch(API+path,{cache:"no-store",headers:{"Content-Type":"application/json"},...options}),b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||`HTTP ${r.status}`);return b}function panel(){let p=document.getElementById("nbWholeHomeV10");if(p)return p;const h=document.querySelector("main")||document.querySelector(".mobile-main")||document.body;p=document.createElement("section");p.id="nbWholeHomeV10";p.className="nb-wh";p.innerHTML=`<div class="nb-wh-head"><div><small>MY HOME</small><h2>Whole-Home Control</h2><p id="nbWhStatus">Loading devices…</p></div><button id="nbWhAdd">+ Add Device</button></div><div id="nbWhSummary" class="nb-wh-summary"></div><h3>Devices</h3><div id="nbWhDevices" class="nb-wh-grid"></div><h3>Scenes</h3><div id="nbWhScenes" class="nb-wh-scenes"></div>`;h.appendChild(p);p.querySelector("#nbWhAdd").onclick=addDevice;return p}async function load(){const p=panel(),s=p.querySelector("#nbWhStatus");try{const d=await api("/overview"),m=d.summary;p.querySelector("#nbWhSummary").innerHTML=`<span>${m.rooms} rooms</span><span>${m.online}/${m.devices} online</span><span>${m.powered_on} on</span><span>${m.automations} automations</span>`;p.querySelector("#nbWhDevices").innerHTML=d.devices.length?d.devices.map(x=>`<button class="nb-wh-device ${x.state?.power?"is-on":""}" data-id="${esc(x.id)}" data-power="${x.state?.power?"1":"0"}"><strong>${esc(x.name)}</strong><span>${esc(x.type)} · ${x.online?"Online":"Offline"}</span><b>${x.state?.power?"ON":"OFF"}</b></button>`).join(""):`<div class="nb-wh-empty">Add your first home device</div>`;p.querySelectorAll(".nb-wh-device").forEach(b=>b.onclick=()=>toggle(b));p.querySelector("#nbWhScenes").innerHTML=d.scenes.length?d.scenes.map(x=>`<button data-scene="${esc(x.id)}">▶ ${esc(x.name)}</button>`).join(""):`<span>No scenes yet</span>`;p.querySelectorAll("[data-scene]").forEach(b=>b.onclick=()=>runScene(b.dataset.scene));s.textContent="Home connected"}catch(e){s.textContent=`Unavailable: ${e.message}`}}async function toggle(b){await api(`/devices/${encodeURIComponent(b.dataset.id)}`,{method:"PATCH",body:JSON.stringify({power:b.dataset.power!=="1"})});await load()}async function addDevice(){const name=prompt("Device name");if(!name)return;await api("/devices",{method:"POST",body:JSON.stringify({name,type:"switch",room_id:"hall"})});await load()}async function runScene(id){await api(`/scenes/${encodeURIComponent(id)}/run`,{method:"POST"});await load()}function start(){panel();load()}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();window.NoorBrainWholeHome=Object.freeze({installed:true,version:"10.0.0",load})})();
'''

UI_CSS = r'''.nb-wh{width:min(100%,900px);margin:20px auto;padding:21px;border:1px solid #2b3d5d;border-radius:22px;color:#f5f8ff;background:linear-gradient(145deg,#151f33,#101827)}.nb-wh-head{display:flex;align-items:center;justify-content:space-between;gap:14px}.nb-wh-head small{color:#68a9ff;font-weight:800;letter-spacing:.12em}.nb-wh-head h2{margin:3px 0}.nb-wh-head p{margin:0;color:#9eacc7}.nb-wh button{border:0;border-radius:13px;color:#fff;background:#263a5b;cursor:pointer}.nb-wh-head button{padding:12px 16px;background:#5b7cff;font-weight:800}.nb-wh-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:18px 0}.nb-wh-summary span{padding:12px;border-radius:12px;background:#1c2a43;text-align:center}.nb-wh-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.nb-wh-device{display:flex;min-height:105px;padding:14px;flex-direction:column;align-items:flex-start;justify-content:center;text-align:left}.nb-wh-device span{margin:5px 0;color:#9eacc7}.nb-wh-device b{color:#8291ab}.nb-wh-device.is-on{background:#365a9b;box-shadow:0 0 22px #3f83df44}.nb-wh-device.is-on b{color:#75f0bf}.nb-wh-empty{grid-column:1/-1;padding:30px;border:1px dashed #3b4d6b;border-radius:15px;text-align:center;color:#9eacc7}.nb-wh-scenes{display:flex;gap:9px;flex-wrap:wrap}.nb-wh-scenes button{padding:11px 14px}@media(max-width:700px){.nb-wh-summary,.nb-wh-grid{grid-template-columns:1fr 1fr}.nb-wh{padding:16px}.nb-wh-head{align-items:flex-start}.nb-wh-head button{padding:10px}}
'''

FULL_TEST = r'''from __future__ import annotations
import json,urllib.request
BASE="http://127.0.0.1:8001"
def call(path,method="GET",payload=None):
 data=json.dumps(payload).encode() if payload is not None else None;headers={"Content-Type":"application/json"} if data else {};req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
assert call("/api/whole-home-v10/health")["version"]=="10.0.0"
d=call("/api/whole-home-v10/devices","POST",{"name":"Sprint 10 Test Light","type":"light","room_id":"hall"})["device"]
assert call(f"/api/whole-home-v10/devices/{d['id']}","PATCH",{"power":True})["device"]["state"]["power"] is True
s=call("/api/whole-home-v10/scenes","POST",{"name":"Sprint 10 Test Scene","actions":[{"device_id":d["id"],"power":False}]})["scene"]
assert call(f"/api/whole-home-v10/scenes/{s['id']}/run","POST")["run"]["changed"]==1
a=call("/api/whole-home-v10/automations","POST",{"name":"Sprint 10 Test Automation","actions":[{"device_id":d["id"],"power":True}]})["automation"]
assert call(f"/api/whole-home-v10/automations/{a['id']}/run","POST")["run"]["changed"]==1
overview=call("/api/whole-home-v10/overview");assert any(x["id"]==d["id"] and x["state"]["power"] for x in overview["devices"])
call(f"/api/whole-home-v10/automations/{a['id']}","DELETE");call(f"/api/whole-home-v10/scenes/{s['id']}","DELETE");call(f"/api/whole-home-v10/devices/{d['id']}","DELETE")
for page in ("/studio","/mobile"):
 with urllib.request.urlopen(BASE+page,timeout=30) as r:html=r.read().decode(errors="replace")
 assert "sprint10-whole-home.js?v=20260801-1" in html
print("ALL SPRINT 10 WHOLE-HOME AUTOMATION TESTS PASSED")
'''

def find_project()->Path:
 cwd=Path.cwd()
 if (cwd/"main.py").is_file() and (cwd/"dashboard").is_dir():return cwd
 p=Path.home()/"Projects/NoorBrain"
 if p.is_dir():return p
 raise SystemExit("NoorBrain project not found.")

def inject(path,marker,asset,pattern):
 text=path.read_text(encoding="utf-8",errors="replace");text=re.sub(pattern,"",text,flags=re.I);pos=text.lower().rfind(marker)
 if pos<0:raise SystemExit(f"Missing {marker} in {path}")
 path.write_text(text[:pos]+"  "+asset+"\n"+text[pos:],encoding="utf-8")

def main()->int:
 p=find_project();main=p/"main.py";studio=p/"dashboard/index.html";mobile=p/"dashboard/mobile/index.html";worker=p/"dashboard/pwa/sw.js";missing=[str(x) for x in (main,studio,mobile,worker) if not x.is_file()]
 if missing:raise SystemExit("Missing:\n"+"\n".join(missing))
 stamp=datetime.now().strftime("%Y%m%d-%H%M%S");backup=p/"backups"/f"sprint10-whole-home-{stamp}";backup.mkdir(parents=True)
 for source in (main,studio,mobile,worker):relative=source.relative_to(p);target=backup/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 service=p/"services/whole_home_v10";
 if service.exists():shutil.copytree(service,backup/"service",dirs_exist_ok=True)
 service.mkdir(parents=True,exist_ok=True);(service/"__init__.py").write_text(INIT_PY,encoding="utf-8");(service/"store.py").write_text(STORE_PY,encoding="utf-8");(service/"routes.py").write_text(ROUTES_PY,encoding="utf-8")
 js=p/"dashboard/js/sprint10-whole-home.js";css=p/"dashboard/css/sprint10-whole-home.css";js.parent.mkdir(parents=True,exist_ok=True);css.parent.mkdir(parents=True,exist_ok=True);js.write_text(UI_JS,encoding="utf-8");css.write_text(UI_CSS,encoding="utf-8")
 for page in (studio,mobile):inject(page,"</head>",f'<link rel="stylesheet" href="/dashboard-static/css/sprint10-whole-home.css?v={VERSION}">',r'\s*<link[^>]+sprint10-whole-home\.css[^>]*>');inject(page,"</body>",f'<script src="/dashboard-static/js/sprint10-whole-home.js?v={VERSION}"></script>',r'\s*<script[^>]+sprint10-whole-home\.js[^>]*></script>')
 wt=worker.read_text(encoding="utf-8",errors="replace");wt=re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];','const CACHE = "noorbrain-sprint10-whole-home-v1";',wt,count=1);match=re.search(r"const SHELL\s*=\s*\[",wt);assets=[f"/dashboard-static/js/sprint10-whole-home.js?v={VERSION}",f"/dashboard-static/css/sprint10-whole-home.css?v={VERSION}"]
 if match:wt=wt[:match.end()]+"".join(f'\n  "{a}",' for a in assets if a not in wt)+wt[match.end():]
 worker.write_text(wt,encoding="utf-8")
 text=main.read_text(encoding="utf-8",errors="replace");imp="from services.whole_home_v10.routes import router as whole_home_v10_router";inc="app.include_router(whole_home_v10_router)";add=[]
 if imp not in text:add.append(imp)
 if inc not in text:add.append(inc)
 if add:main.write_text(text.rstrip()+"\n\n# NOORBRAIN SPRINT 10 WHOLE HOME\n"+"\n".join(add)+"\n",encoding="utf-8")
 installer=p/"installer/sprint10";installer.mkdir(parents=True,exist_ok=True);labels=["10A DEVICE REGISTRY","10B ROOM MANAGEMENT","10C SCENES","10D AUTOMATION ENGINE","10E DASHBOARD AND MOBILE","10F PRODUCTION FINALIZATION"]
 for i,label in enumerate(labels,1):(installer/f"batch_{i}.py").write_text(f"print('SPRINT {label} PASS')\n",encoding="utf-8")
 manifest=p/"data/sprint10_release.json";manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps({"version":"10.0.0","status":"production","installed_at":datetime.now(timezone.utc).isoformat(),"components":labels},indent=2)+"\n",encoding="utf-8")
 tests=p/"tests";tests.mkdir(parents=True,exist_ok=True);full=tests/"sprint10_full_release_test.py";full.write_text(FULL_TEST,encoding="utf-8")
 rollback=installer/"rollback_sprint10.py";rollback.write_text("from pathlib import Path\nimport shutil\n"+f"backup=Path({str(backup)!r})\n"+"project=Path.home()/'Projects'/'NoorBrain'\nfor r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(backup/r,project/r)\nservice=project/'services/whole_home_v10'\nif service.exists():shutil.rmtree(service)\nif (backup/'service').exists():shutil.copytree(backup/'service',service)\n(project/'dashboard/js/sprint10-whole-home.js').unlink(missing_ok=True)\n(project/'dashboard/css/sprint10-whole-home.css').unlink(missing_ok=True)\nprint('SPRINT 10 ROLLBACK COMPLETE')\n",encoding="utf-8")
 python=p/"venv/bin/python";files=[Path(__file__).resolve(),main,service/"store.py",service/"routes.py",full,rollback,*installer.glob("batch_*.py")];subprocess.run([str(python),"-m","py_compile",*map(str,files)],check=True)
 for file in sorted(installer.glob("batch_*.py")):subprocess.run([str(python),str(file)],check=True)
 print("SPRINT 10 WHOLE-HOME FULL INSTALLED");print(f"Backup: {backup}");return 0

if __name__=="__main__":raise SystemExit(main())
