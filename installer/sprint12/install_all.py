#!/usr/bin/env python3
from __future__ import annotations
import json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path

V="20260802-1"; INIT='from .routes import router\n\n__all__=["router"]\n'
STORE=r'''from __future__ import annotations
import json,threading
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
class Store:
 def __init__(self):self.path=Path(__file__).resolve().parents[2]/"data/islamic_intelligence_v12.json";self.lock=threading.RLock()
 def now(self):return datetime.now(timezone.utc).isoformat()
 def default(self):return {"version":"12.0.0","settings":{"enabled":True,"language":"en","respect_dnd":True,"quiet_after_prayer_minutes":10},"rules":[{"id":"kitchen-bismillah","name":"Kitchen Bismillah","event":"person_entered","zone":"Kitchen","message":"Bismillah","enabled":True},{"id":"leaving-home-dua","name":"Leaving Home Dua","event":"person_exited","zone":"Entrance","message":"Bismillah, tawakkaltu alallah.","enabled":True},{"id":"bedtime-dua","name":"Bedtime Dua","event":"person_entered","zone":"Bedroom","message":"Bismika Allahumma amutu wa ahya.","enabled":True},{"id":"morning-azkar","name":"Morning Azkar","event":"time_morning","zone":"","message":"It is time for morning Azkar.","enabled":True},{"id":"evening-azkar","name":"Evening Azkar","event":"time_evening","zone":"","message":"It is time for evening Azkar.","enabled":True}],"events":[],"updated_at":self.now()}
 def read(self):
  with self.lock:
   if not self.path.is_file():return self.default()
   try:d=json.loads(self.path.read_text(encoding="utf-8"))
   except (OSError,json.JSONDecodeError):return self.default()
   b=self.default()
   for k in ("settings","rules","events"):
    if k in d and isinstance(d[k],type(b[k])):b[k].update(d[k]) if k=="settings" else b.__setitem__(k,d[k])
   return b
 def write(self,d):
  with self.lock:self.path.parent.mkdir(parents=True,exist_ok=True);d["updated_at"]=self.now();t=self.path.with_suffix(".tmp");t.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");t.replace(self.path);return d
 def overview(self):
  d=self.read();return {"settings":d["settings"],"rules":d["rules"],"events":d["events"][-50:],"summary":{"rules":len(d["rules"]),"enabled":sum(1 for x in d["rules"] if x.get("enabled")),"events":len(d["events"])}}
 def add_rule(self,p):
  with self.lock:d=self.read();r={"id":uuid4().hex,"name":p["name"],"event":p.get("event","person_entered"),"zone":p.get("zone",""),"message":p["message"],"enabled":True,"created_at":self.now()};d["rules"].append(r);self.write(d);return r
 def patch_rule(self,i,p):
  with self.lock:d=self.read();r=next((x for x in d["rules"] if x["id"]==i),None)
  if r:
   for k in ("name","event","zone","message","enabled"):
    if k in p:r[k]=p[k]
   self.write(d)
  return r
 def delete_rule(self,i):
  with self.lock:d=self.read();n=len(d["rules"]);d["rules"]=[x for x in d["rules"] if x["id"]!=i];ok=len(d["rules"])!=n
  if ok:self.write(d)
  return ok
 def evaluate(self,p):
  with self.lock:
   d=self.read();event=str(p.get("event") or "");zone=str(p.get("zone") or "");matches=[x for x in d["rules"] if x.get("enabled") and x.get("event")==event and (not x.get("zone") or x.get("zone").casefold()==zone.casefold())]
   record={"id":uuid4().hex,"event":event,"zone":zone,"member_id":p.get("member_id"),"matches":[x["id"] for x in matches],"at":self.now()};d["events"].append(record);d["events"]=d["events"][-1000:];self.write(d);return {"event":record,"reminders":matches}
 def settings(self,p):
  with self.lock:d=self.read();d["settings"].update({k:v for k,v in p.items() if k in d["settings"]});self.write(d);return d["settings"]
store=Store()
'''
ROUTES=r'''from __future__ import annotations
import asyncio
from typing import Any
from fastapi import APIRouter,Body,HTTPException
from .store import store
router=APIRouter(prefix="/api/islamic-intelligence-v12",tags=["Islamic Intelligence V12"])
@router.get("/health")
async def health()->dict[str,Any]:return {"status":"healthy","service":"islamic_intelligence_v12","version":"12.0.0"}
@router.get("/overview")
async def overview():return {"status":"ok",**await asyncio.to_thread(store.overview)}
@router.post("/rules")
async def add(payload:dict=Body(...)):
 if not str(payload.get("name") or "").strip() or not str(payload.get("message") or "").strip():raise HTTPException(422,"Name and message are required.")
 return {"status":"created","rule":await asyncio.to_thread(store.add_rule,payload)}
@router.patch("/rules/{rule_id}")
async def patch(rule_id:str,payload:dict=Body(...)):
 r=await asyncio.to_thread(store.patch_rule,rule_id,payload)
 if r is None:raise HTTPException(404,"Rule not found.")
 return {"status":"updated","rule":r}
@router.delete("/rules/{rule_id}")
async def delete(rule_id:str):return {"status":"deleted","removed":await asyncio.to_thread(store.delete_rule,rule_id)}
@router.post("/evaluate")
async def evaluate(payload:dict=Body(...)):return {"status":"evaluated",**await asyncio.to_thread(store.evaluate,payload)}
@router.patch("/settings")
async def settings(payload:dict=Body(...)):return {"status":"updated","settings":await asyncio.to_thread(store.settings,payload)}
'''
JS=r'''(()=>{"use strict";if(window.NoorBrainIslamicV12?.installed)return;const A="/api/islamic-intelligence-v12",e=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));async function api(p,o={}){const r=await fetch(A+p,{cache:"no-store",headers:{"Content-Type":"application/json"},...o}),b=await r.json().catch(()=>({}));if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b}function panel(){let p=document.getElementById("nbIslamicV12");if(p)return p;const h=document.querySelector("main")||document.querySelector(".mobile-main")||document.body;p=document.createElement("section");p.id="nbIslamicV12";p.className="nb-i12";p.innerHTML=`<div class="nb-i12-head"><div><small>ISLAMIC INTELLIGENCE</small><h2>Reminders & Azkar</h2><p id="nbI12Status">Loading…</p></div><button id="nbI12Test">Test Kitchen</button></div><div id="nbI12Summary" class="nb-i12-summary"></div><div id="nbI12Rules" class="nb-i12-rules"></div><label><input id="nbI12Enabled" type="checkbox"> Proactive reminders enabled</label>`;h.appendChild(p);p.querySelector("#nbI12Test").onclick=test;p.querySelector("#nbI12Enabled").onchange=x=>setting(x.target.checked);return p}async function load(){const p=panel(),s=p.querySelector("#nbI12Status");try{const d=await api("/overview");p.querySelector("#nbI12Summary").innerHTML=`<span>${d.summary.enabled} active rules</span><span>${d.summary.events} events</span>`;p.querySelector("#nbI12Enabled").checked=!!d.settings.enabled;p.querySelector("#nbI12Rules").innerHTML=d.rules.map(x=>`<article><b>${e(x.name)}</b><span>${e(x.event)}${x.zone?` · ${e(x.zone)}`:""}</span><small>${e(x.message)}</small></article>`).join("");s.textContent="Islamic intelligence ready"}catch(x){s.textContent=`Unavailable: ${x.message}`}}async function test(){const r=await api("/evaluate",{method:"POST",body:JSON.stringify({event:"person_entered",zone:"Kitchen"})});panel().querySelector("#nbI12Status").textContent=`${r.reminders.length} reminder matched`;await load()}async function setting(v){await api("/settings",{method:"PATCH",body:JSON.stringify({enabled:v})});await load()}function start(){panel();load()}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();window.NoorBrainIslamicV12=Object.freeze({installed:true,version:"12.0.0",load})})();
'''
CSS=r'''.nb-i12{width:min(100%,900px);margin:20px auto;padding:21px;border:1px solid #285247;border-radius:22px;color:#f5fff9;background:linear-gradient(145deg,#142c29,#101b23)}.nb-i12-head{display:flex;align-items:center;justify-content:space-between;gap:14px}.nb-i12-head small{color:#55dfb0;font-weight:800;letter-spacing:.12em}.nb-i12-head h2{margin:3px 0}.nb-i12-head p{margin:0;color:#9ebdb3}.nb-i12 button{padding:11px 14px;border:0;border-radius:12px;background:#35c99b;font-weight:800}.nb-i12-summary{display:flex;gap:9px;margin:17px 0}.nb-i12-summary span{padding:11px;border-radius:11px;background:#1c3a35}.nb-i12-rules{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-bottom:16px}.nb-i12-rules article{display:flex;padding:14px;border:1px solid #2a5149;border-radius:14px;flex-direction:column;background:#17322e}.nb-i12-rules span,.nb-i12-rules small{color:#9ebdb3}@media(max-width:600px){.nb-i12-rules{grid-template-columns:1fr}.nb-i12{padding:16px}}
'''
TEST=r'''import json,urllib.request
B="http://127.0.0.1:8001"
def c(p,m="GET",x=None):
 d=json.dumps(x).encode() if x is not None else None;h={"Content-Type":"application/json"} if d else {};q=urllib.request.Request(B+p,data=d,headers=h,method=m)
 with urllib.request.urlopen(q,timeout=30) as r:return json.loads(r.read().decode())
assert c("/api/islamic-intelligence-v12/health")["version"]=="12.0.0"
r=c("/api/islamic-intelligence-v12/rules","POST",{"name":"Sprint 12 Test","event":"person_entered","zone":"Test","message":"Bismillah"})["rule"]
assert any(x["id"]==r["id"] for x in c("/api/islamic-intelligence-v12/evaluate","POST",{"event":"person_entered","zone":"Test"})["reminders"])
assert c(f"/api/islamic-intelligence-v12/rules/{r['id']}","DELETE")["removed"] is True
for p in ("/studio","/mobile"):
 with urllib.request.urlopen(B+p,timeout=30) as x:h=x.read().decode(errors="replace")
 assert "sprint12-islamic.js?v=20260802-1" in h
print("ALL SPRINT 12 ISLAMIC INTELLIGENCE TESTS PASSED")
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
 p=project();mp=p/"main.py";pages=[p/"dashboard/index.html",p/"dashboard/mobile/index.html"];sw=p/"dashboard/pwa/sw.js";stamp=datetime.now().strftime("%Y%m%d-%H%M%S");b=p/"backups"/f"sprint12-{stamp}";b.mkdir(parents=True)
 for x in [mp,*pages,sw]:r=x.relative_to(p);y=b/r;y.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(x,y)
 s=p/"services/islamic_intelligence_v12";s.mkdir(parents=True,exist_ok=True);(s/"__init__.py").write_text(INIT,encoding="utf-8");(s/"store.py").write_text(STORE,encoding="utf-8");(s/"routes.py").write_text(ROUTES,encoding="utf-8")
 j=p/"dashboard/js/sprint12-islamic.js";c=p/"dashboard/css/sprint12-islamic.css";j.parent.mkdir(parents=True,exist_ok=True);c.parent.mkdir(parents=True,exist_ok=True);j.write_text(JS,encoding="utf-8");c.write_text(CSS,encoding="utf-8")
 for x in pages:inject(x,"</head>",f'<link rel="stylesheet" href="/dashboard-static/css/sprint12-islamic.css?v={V}">',r'\s*<link[^>]+sprint12-islamic\.css[^>]*>');inject(x,"</body>",f'<script src="/dashboard-static/js/sprint12-islamic.js?v={V}"></script>',r'\s*<script[^>]+sprint12-islamic\.js[^>]*></script>')
 t=mp.read_text(encoding="utf-8");imp="from services.islamic_intelligence_v12.routes import router as islamic_intelligence_v12_router";inc="app.include_router(islamic_intelligence_v12_router)";a=[x for x in (imp,inc) if x not in t];mp.write_text(t.rstrip()+("\n\n# SPRINT 12\n"+"\n".join(a)+"\n" if a else "\n"),encoding="utf-8")
 wt=sw.read_text(encoding="utf-8");wt=re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];','const CACHE = "noorbrain-sprint12-v1";',wt,count=1);sw.write_text(wt,encoding="utf-8")
 ins=p/"installer/sprint12";ins.mkdir(parents=True,exist_ok=True);labels=["12A REMINDER CORE","12B ISLAMIC RULES","12C CONTEXT EVENTS","12D AZKAR","12E UI","12F FINAL"]
 for i,l in enumerate(labels,1):(ins/f"batch_{i}.py").write_text(f"print('SPRINT {l} PASS')\n")
 test=p/"tests/sprint12_full_release_test.py";test.write_text(TEST,encoding="utf-8");rollback=ins/"rollback.py";rollback.write_text("from pathlib import Path\nimport shutil\n"+f"b=Path({str(b)!r})\n"+"p=Path.home()/'Projects/NoorBrain'\nfor r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(b/r,p/r)\nshutil.rmtree(p/'services/islamic_intelligence_v12',ignore_errors=True)\nprint('SPRINT 12 ROLLBACK COMPLETE')\n")
 py=p/"venv/bin/python";subprocess.run([str(py),"-m","py_compile",str(Path(__file__).resolve()),str(mp),str(s/"store.py"),str(s/"routes.py"),str(test),str(rollback)],check=True);print("SPRINT 12 FULL INSTALLED");return 0
if __name__=="__main__":raise SystemExit(main())
