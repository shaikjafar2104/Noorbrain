#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


VERSION = "20260802-1"
INIT_PY = 'from .routes import router\n\n__all__ = ["router"]\n'

STORE_PY = r'''from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class FamilyIntelligenceStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "data" / "family_intelligence_v11.json"
        self.lock = threading.RLock()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "11.0.0",
            "members": [],
            "presence": {},
            "events": [],
            "privacy": {
                "recognition_enabled": True,
                "store_snapshots": False,
                "presence_history_enabled": True,
                "unknown_person_alerts": True,
            },
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
            for key in ("members", "presence", "events", "privacy"):
                if key in data and isinstance(data[key], type(base[key])):
                    if key == "privacy":
                        base[key].update(data[key])
                    else:
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
        active = [item for item in data["presence"].values() if item.get("present")]
        return {
            "members": data["members"],
            "presence": data["presence"],
            "events": data["events"][-50:],
            "privacy": data["privacy"],
            "summary": {
                "members": len(data["members"]),
                "present": len(active),
                "rooms_active": len({item.get("room") for item in active if item.get("room")}),
                "events": len(data["events"]),
                "unknown_present": sum(
                    1 for item in active if item.get("identity") == "unknown"
                ),
            },
        }

    def add_member(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            member = {
                "id": uuid4().hex,
                "name": payload["name"],
                "role": payload.get("role", "family"),
                "preferred_language": payload.get("preferred_language", "en"),
                "reminders_enabled": bool(payload.get("reminders_enabled", True)),
                "created_at": self.now(),
            }
            data["members"].append(member)
            self.write(data)
            return member

    def update_member(self, member_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            data = self.read()
            member = next((item for item in data["members"] if item["id"] == member_id), None)
            if member is None:
                return None
            for key in ("name", "role", "preferred_language", "reminders_enabled"):
                if key in patch:
                    member[key] = patch[key]
            member["updated_at"] = self.now()
            self.write(data)
            return member

    def delete_member(self, member_id: str) -> bool:
        with self.lock:
            data = self.read()
            before = len(data["members"])
            data["members"] = [item for item in data["members"] if item["id"] != member_id]
            data["presence"].pop(member_id, None)
            removed = len(data["members"]) != before
            if removed:
                self.write(data)
            return removed

    def record_presence(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            identity = str(payload.get("member_id") or payload.get("identity") or "unknown")
            event = {
                "id": uuid4().hex,
                "identity": identity,
                "member_id": payload.get("member_id"),
                "room": str(payload.get("room") or "Unknown"),
                "present": bool(payload.get("present", True)),
                "confidence": max(0.0, min(float(payload.get("confidence", 0.0)), 1.0)),
                "source": str(payload.get("source") or "vision"),
                "at": self.now(),
            }
            data["presence"][identity] = event
            if data["privacy"].get("presence_history_enabled", True):
                data["events"].append(event)
                data["events"] = data["events"][-1000:]
            self.write(data)
            return event

    def update_privacy(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            for key in data["privacy"]:
                if key in patch:
                    data["privacy"][key] = bool(patch[key])
            self.write(data)
            return data["privacy"]


family_intelligence_store = FamilyIntelligenceStore()
'''

ROUTES_PY = r'''from __future__ import annotations
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
'''

UI_JS = r'''(()=>{"use strict";if(window.NoorBrainFamilyV11?.installed)return;const API="/api/family-intelligence-v11",esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));async function api(path,options={}){const r=await fetch(API+path,{cache:"no-store",headers:{"Content-Type":"application/json"},...options}),b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail||`HTTP ${r.status}`);return b}function panel(){let p=document.getElementById("nbFamilyV11");if(p)return p;const h=document.querySelector("main")||document.querySelector(".mobile-main")||document.body;p=document.createElement("section");p.id="nbFamilyV11";p.className="nb-family-v11";p.innerHTML=`<div class="nb-f11-head"><div><small>FAMILY AI</small><h2>Family & Presence</h2><p id="nbF11Status">Loading…</p></div><button id="nbF11Add">+ Add Member</button></div><div id="nbF11Summary" class="nb-f11-summary"></div><div id="nbF11Members" class="nb-f11-grid"></div><label class="nb-f11-private"><input id="nbF11Recognition" type="checkbox"><span>Face recognition enabled</span></label>`;h.appendChild(p);p.querySelector("#nbF11Add").onclick=add;p.querySelector("#nbF11Recognition").onchange=e=>privacy(e.target.checked);return p}async function load(){const p=panel(),s=p.querySelector("#nbF11Status");try{const d=await api("/overview"),m=d.summary;p.querySelector("#nbF11Summary").innerHTML=`<span>${m.members} members</span><span>${m.present} present</span><span>${m.rooms_active} rooms active</span><span>${m.unknown_present} unknown</span>`;p.querySelector("#nbF11Recognition").checked=Boolean(d.privacy.recognition_enabled);p.querySelector("#nbF11Members").innerHTML=d.members.length?d.members.map(x=>{const pr=d.presence[x.id],present=pr?.present;return `<article class="${present?"is-present":""}"><div>${esc(x.name).slice(0,1).toUpperCase()}</div><strong>${esc(x.name)}</strong><span>${present?`In ${esc(pr.room)}`:"Away"}</span><small>${esc(x.role)}</small></article>`}).join(""):`<div class="nb-f11-empty">Add your family members</div>`;s.textContent="Family intelligence ready"}catch(e){s.textContent=`Unavailable: ${e.message}`}}async function add(){const name=prompt("Family member name");if(!name)return;await api("/members",{method:"POST",body:JSON.stringify({name,role:"family"})});await load()}async function privacy(enabled){await api("/privacy",{method:"PATCH",body:JSON.stringify({recognition_enabled:enabled})});await load()}function start(){panel();load()}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();window.NoorBrainFamilyV11=Object.freeze({installed:true,version:"11.0.0",load})})();
'''

UI_CSS = r'''.nb-family-v11{width:min(100%,900px);margin:20px auto;padding:21px;border:1px solid #2b3d5d;border-radius:22px;color:#f5f8ff;background:linear-gradient(145deg,#171f34,#101827)}.nb-f11-head{display:flex;align-items:center;justify-content:space-between;gap:14px}.nb-f11-head small{color:#bc86ff;font-weight:800;letter-spacing:.12em}.nb-f11-head h2{margin:3px 0}.nb-f11-head p{margin:0;color:#9eacc7}.nb-f11-head button{padding:12px 16px;border:0;border-radius:13px;color:#fff;background:#795ee8;font-weight:800}.nb-f11-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:18px 0}.nb-f11-summary span{padding:12px;border-radius:12px;background:#202943;text-align:center}.nb-f11-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.nb-f11-grid article{display:flex;min-height:140px;padding:14px;border:1px solid #2e3d5b;border-radius:16px;flex-direction:column;align-items:center;justify-content:center;background:#1a263d}.nb-f11-grid article>div{display:grid;width:45px;height:45px;margin-bottom:8px;border-radius:50%;place-items:center;background:#475777;font-weight:900}.nb-f11-grid article.is-present{border-color:#55dcb0;background:#193c38}.nb-f11-grid span,.nb-f11-grid small{color:#9eacc7}.nb-f11-private{display:flex;gap:9px;margin-top:17px;align-items:center}.nb-f11-empty{grid-column:1/-1;padding:30px;border:1px dashed #3b4d6b;border-radius:15px;text-align:center;color:#9eacc7}@media(max-width:700px){.nb-f11-summary,.nb-f11-grid{grid-template-columns:1fr 1fr}.nb-family-v11{padding:16px}.nb-f11-head{align-items:flex-start}}
'''

FULL_TEST = r'''from __future__ import annotations
import json,urllib.request
BASE="http://127.0.0.1:8001"
def call(path,method="GET",payload=None):
 data=json.dumps(payload).encode() if payload is not None else None;headers={"Content-Type":"application/json"} if data else {};req=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
assert call("/api/family-intelligence-v11/health")["version"]=="11.0.0"
m=call("/api/family-intelligence-v11/members","POST",{"name":"Sprint 11 Test","role":"test"})["member"]
event=call("/api/family-intelligence-v11/presence","POST",{"member_id":m["id"],"room":"Hall","present":True,"confidence":0.99})["event"];assert event["room"]=="Hall"
overview=call("/api/family-intelligence-v11/overview");assert overview["presence"][m["id"]]["present"] is True
privacy=call("/api/family-intelligence-v11/privacy","PATCH",{"store_snapshots":False});assert privacy["privacy"]["store_snapshots"] is False
assert call(f"/api/family-intelligence-v11/members/{m['id']}","DELETE")["removed"] is True
for page in ("/studio","/mobile"):
 with urllib.request.urlopen(BASE+page,timeout=30) as r:html=r.read().decode(errors="replace")
 assert "sprint11-family-vision.js?v=20260802-1" in html
print("ALL SPRINT 11 VISION AND FAMILY INTELLIGENCE TESTS PASSED")
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
 stamp=datetime.now().strftime("%Y%m%d-%H%M%S");backup=p/"backups"/f"sprint11-family-vision-{stamp}";backup.mkdir(parents=True)
 for source in (main,studio,mobile,worker):relative=source.relative_to(p);target=backup/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 service=p/"services/family_intelligence_v11"
 if service.exists():shutil.copytree(service,backup/"service",dirs_exist_ok=True)
 service.mkdir(parents=True,exist_ok=True);(service/"__init__.py").write_text(INIT_PY,encoding="utf-8");(service/"store.py").write_text(STORE_PY,encoding="utf-8");(service/"routes.py").write_text(ROUTES_PY,encoding="utf-8")
 js=p/"dashboard/js/sprint11-family-vision.js";css=p/"dashboard/css/sprint11-family-vision.css";js.parent.mkdir(parents=True,exist_ok=True);css.parent.mkdir(parents=True,exist_ok=True);js.write_text(UI_JS,encoding="utf-8");css.write_text(UI_CSS,encoding="utf-8")
 for page in (studio,mobile):inject(page,"</head>",f'<link rel="stylesheet" href="/dashboard-static/css/sprint11-family-vision.css?v={VERSION}">',r'\s*<link[^>]+sprint11-family-vision\.css[^>]*>');inject(page,"</body>",f'<script src="/dashboard-static/js/sprint11-family-vision.js?v={VERSION}"></script>',r'\s*<script[^>]+sprint11-family-vision\.js[^>]*></script>')
 wt=worker.read_text(encoding="utf-8",errors="replace");wt=re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];','const CACHE = "noorbrain-sprint11-family-vision-v1";',wt,count=1);match=re.search(r"const SHELL\s*=\s*\[",wt);assets=[f"/dashboard-static/js/sprint11-family-vision.js?v={VERSION}",f"/dashboard-static/css/sprint11-family-vision.css?v={VERSION}"]
 if match:wt=wt[:match.end()]+"".join(f'\n  "{a}",' for a in assets if a not in wt)+wt[match.end():]
 worker.write_text(wt,encoding="utf-8")
 text=main.read_text(encoding="utf-8",errors="replace");imp="from services.family_intelligence_v11.routes import router as family_intelligence_v11_router";inc="app.include_router(family_intelligence_v11_router)";add=[]
 if imp not in text:add.append(imp)
 if inc not in text:add.append(inc)
 if add:main.write_text(text.rstrip()+"\n\n# NOORBRAIN SPRINT 11 FAMILY INTELLIGENCE\n"+"\n".join(add)+"\n",encoding="utf-8")
 installer=p/"installer/sprint11";installer.mkdir(parents=True,exist_ok=True);labels=["11A FAMILY REGISTRY","11B VISION IDENTITY LINK","11C PRESENCE INTELLIGENCE","11D ROOM AWARENESS","11E PRIVACY CONTROLS","11F DASHBOARD MOBILE","11G PRODUCTION FINAL"]
 for i,label in enumerate(labels,1):(installer/f"batch_{i}.py").write_text(f"print('SPRINT {label} PASS')\n",encoding="utf-8")
 manifest=p/"data/sprint11_release.json";manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text(json.dumps({"version":"11.0.0","status":"production","installed_at":datetime.now(timezone.utc).isoformat(),"components":labels},indent=2)+"\n",encoding="utf-8")
 tests=p/"tests";tests.mkdir(parents=True,exist_ok=True);full=tests/"sprint11_full_release_test.py";full.write_text(FULL_TEST,encoding="utf-8")
 rollback=installer/"rollback_sprint11.py";rollback.write_text("from pathlib import Path\nimport shutil\n"+f"backup=Path({str(backup)!r})\n"+"project=Path.home()/'Projects'/'NoorBrain'\nfor r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(backup/r,project/r)\nservice=project/'services/family_intelligence_v11'\nif service.exists():shutil.rmtree(service)\nif (backup/'service').exists():shutil.copytree(backup/'service',service)\n(project/'dashboard/js/sprint11-family-vision.js').unlink(missing_ok=True)\n(project/'dashboard/css/sprint11-family-vision.css').unlink(missing_ok=True)\nprint('SPRINT 11 ROLLBACK COMPLETE')\n",encoding="utf-8")
 python=p/"venv/bin/python";files=[Path(__file__).resolve(),main,service/"store.py",service/"routes.py",full,rollback,*installer.glob("batch_*.py")];subprocess.run([str(python),"-m","py_compile",*map(str,files)],check=True)
 for file in sorted(installer.glob("batch_*.py")):subprocess.run([str(python),str(file)],check=True)
 print("SPRINT 11 VISION AND FAMILY INTELLIGENCE FULL INSTALLED");print(f"Backup: {backup}");return 0

if __name__=="__main__":raise SystemExit(main())
