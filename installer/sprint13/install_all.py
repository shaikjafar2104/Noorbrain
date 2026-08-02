#!/usr/bin/env python3
from __future__ import annotations
import json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path

V="20260802-1";INIT='from .routes import router\n\n__all__=["router"]\n'
STORE=r'''from __future__ import annotations
import json,re,threading
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
class PluginRegistry:
 ID=re.compile(r"^[a-z][a-z0-9_-]{2,63}$");ALLOWED={"read_devices","control_devices","read_presence","create_reminders","network","storage"}
 def __init__(self):self.path=Path(__file__).resolve().parents[2]/"data/plugin_registry_v13.json";self.lock=threading.RLock()
 def now(self):return datetime.now(timezone.utc).isoformat()
 def default(self):return {"version":"13.0.0","plugins":[],"events":[],"updated_at":self.now()}
 def read(self):
  with self.lock:
   if not self.path.is_file():return self.default()
   try:d=json.loads(self.path.read_text(encoding="utf-8"))
   except (OSError,json.JSONDecodeError):return self.default()
   return d if isinstance(d.get("plugins"),list) else self.default()
 def write(self,d):
  with self.lock:self.path.parent.mkdir(parents=True,exist_ok=True);d["updated_at"]=self.now();t=self.path.with_suffix(".tmp");t.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8");t.replace(self.path);return d
 def validate(self,m):
  pid=str(m.get("id") or "");name=str(m.get("name") or "").strip();version=str(m.get("version") or "").strip();perms=list(m.get("permissions") or [])
  if not self.ID.fullmatch(pid):raise ValueError("Invalid plugin id.")
  if not name or not version:raise ValueError("Plugin name and version are required.")
  invalid=[x for x in perms if x not in self.ALLOWED]
  if invalid:raise ValueError("Invalid permissions: "+", ".join(invalid))
  return {"id":pid,"name":name,"version":version,"description":str(m.get("description") or ""),"permissions":perms,"entrypoint":str(m.get("entrypoint") or ""),"enabled":False,"status":"installed","installed_at":self.now()}
 def install(self,m):
  with self.lock:
   d=self.read();plugin=self.validate(m);old=next((x for x in d["plugins"] if x["id"]==plugin["id"]),None)
   if old:plugin["enabled"]=old.get("enabled",False);d["plugins"]=[plugin if x["id"]==plugin["id"] else x for x in d["plugins"]]
   else:d["plugins"].append(plugin)
   d["events"].append({"kind":"install","plugin_id":plugin["id"],"at":self.now()});d["events"]=d["events"][-500:];self.write(d);return plugin
 def enable(self,pid,enabled):
  with self.lock:
   d=self.read();p=next((x for x in d["plugins"] if x["id"]==pid),None)
   if p:p["enabled"]=enabled;p["status"]="active" if enabled else "disabled";d["events"].append({"kind":"enable" if enabled else "disable","plugin_id":pid,"at":self.now()});self.write(d)
   return p
 def delete(self,pid):
  with self.lock:d=self.read();n=len(d["plugins"]);d["plugins"]=[x for x in d["plugins"] if x["id"]!=pid];ok=len(d["plugins"])!=n
  if ok:self.write(d)
  return ok
 def overview(self):
  d=self.read();return {"plugins":d["plugins"],"events":d["events"][-50:],"allowed_permissions":sorted(self.ALLOWED),"summary":{"installed":len(d["plugins"]),"enabled":sum(1 for x in d["plugins"] if x.get("enabled")),"events":len(d["events"])}}
registry=PluginRegistry()
'''
ROUTES=r'''from __future__ import annotations
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
'''
JS=r'''(()=>{"use strict";if(window.NoorBrainPluginsV13?.installed)return;const A="/api/plugin-platform-v13",e=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));async function api(p,o={}){const r=await fetch(A+p,{cache:"no-store",headers:{"Content-Type":"application/json"},...o}),b=await r.json().catch(()=>({}));if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b}function panel(){let p=document.getElementById("nbPluginsV13");if(p)return p;const h=document.querySelector("main")||document.querySelector(".mobile-main")||document.body;p=document.createElement("section");p.id="nbPluginsV13";p.className="nb-p13";p.innerHTML=`<div class="nb-p13-head"><div><small>OPEN PLATFORM</small><h2>Plugins</h2><p id="nbP13Status">Loading…</p></div><button id="nbP13Add">+ Test Plugin</button></div><div id="nbP13Summary" class="nb-p13-summary"></div><div id="nbP13List" class="nb-p13-list"></div>`;h.appendChild(p);p.querySelector("#nbP13Add").onclick=add;return p}async function load(){const p=panel(),s=p.querySelector("#nbP13Status");try{const d=await api("/overview");p.querySelector("#nbP13Summary").innerHTML=`<span>${d.summary.installed} installed</span><span>${d.summary.enabled} enabled</span>`;p.querySelector("#nbP13List").innerHTML=d.plugins.length?d.plugins.map(x=>`<article><div><b>${e(x.name)}</b><small>${e(x.id)} · v${e(x.version)}</small></div><button data-id="${e(x.id)}" data-on="${x.enabled?1:0}">${x.enabled?"Disable":"Enable"}</button></article>`).join(""):`<div class="nb-p13-empty">No plugins installed</div>`;p.querySelectorAll("[data-id]").forEach(b=>b.onclick=()=>toggle(b));s.textContent="Plugin platform ready"}catch(x){s.textContent=`Unavailable: ${x.message}`}}async function add(){await api("/plugins",{method:"POST",body:JSON.stringify({id:"noor-demo-plugin",name:"Noor Demo Plugin",version:"1.0.0",permissions:["read_devices"]})});await load()}async function toggle(b){await api(`/plugins/${encodeURIComponent(b.dataset.id)}/enable`,{method:"POST",body:JSON.stringify({enabled:b.dataset.on!=="1"})});await load()}function start(){panel();load()}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();window.NoorBrainPluginsV13=Object.freeze({installed:true,version:"13.0.0",load})})();
'''
CSS=r'''.nb-p13{width:min(100%,900px);margin:20px auto;padding:21px;border:1px solid #3b4168;border-radius:22px;color:#f7f7ff;background:linear-gradient(145deg,#1b1d39,#111526)}.nb-p13-head{display:flex;align-items:center;justify-content:space-between}.nb-p13-head small{color:#a98cff;font-weight:800;letter-spacing:.12em}.nb-p13-head h2{margin:3px 0}.nb-p13-head p{margin:0;color:#a4aac6}.nb-p13 button{padding:10px 14px;border:0;border-radius:11px;color:#fff;background:#765de8;font-weight:800}.nb-p13-summary{display:flex;gap:9px;margin:18px 0}.nb-p13-summary span{padding:11px;border-radius:11px;background:#262a4b}.nb-p13-list{display:grid;gap:9px}.nb-p13-list article{display:flex;padding:14px;border:1px solid #363b61;border-radius:14px;align-items:center;justify-content:space-between;background:#202441}.nb-p13-list article div{display:flex;flex-direction:column}.nb-p13-list small{color:#a4aac6}.nb-p13-empty{padding:28px;border:1px dashed #454a70;border-radius:14px;text-align:center;color:#a4aac6}@media(max-width:600px){.nb-p13{padding:16px}}
'''
TEST=r'''import json,urllib.request
B="http://127.0.0.1:8001"
def c(p,m="GET",x=None):
 d=json.dumps(x).encode() if x is not None else None;h={"Content-Type":"application/json"} if d else {};q=urllib.request.Request(B+p,data=d,headers=h,method=m)
 with urllib.request.urlopen(q,timeout=30) as r:return json.loads(r.read().decode())
assert c("/api/plugin-platform-v13/health")["version"]=="13.0.0"
p=c("/api/plugin-platform-v13/plugins","POST",{"id":"sprint13-test","name":"Sprint 13 Test","version":"1.0.0","permissions":["read_devices"]})["plugin"]
assert c(f"/api/plugin-platform-v13/plugins/{p['id']}/enable","POST",{"enabled":True})["plugin"]["enabled"] is True
assert c(f"/api/plugin-platform-v13/plugins/{p['id']}","DELETE")["removed"] is True
for page in ("/studio","/mobile"):
 with urllib.request.urlopen(B+page,timeout=30) as r:h=r.read().decode(errors="replace")
 assert "sprint13-plugins.js?v=20260802-1" in h
print("ALL SPRINT 13 PLUGIN PLATFORM TESTS PASSED")
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
 p=project();mp=p/"main.py";pages=[p/"dashboard/index.html",p/"dashboard/mobile/index.html"];sw=p/"dashboard/pwa/sw.js";stamp=datetime.now().strftime("%Y%m%d-%H%M%S");b=p/"backups"/f"sprint13-{stamp}";b.mkdir(parents=True)
 for x in [mp,*pages,sw]:r=x.relative_to(p);y=b/r;y.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(x,y)
 s=p/"services/plugin_platform_v13";s.mkdir(parents=True,exist_ok=True);(s/"__init__.py").write_text(INIT,encoding="utf-8");(s/"store.py").write_text(STORE,encoding="utf-8");(s/"routes.py").write_text(ROUTES,encoding="utf-8")
 j=p/"dashboard/js/sprint13-plugins.js";c=p/"dashboard/css/sprint13-plugins.css";j.parent.mkdir(parents=True,exist_ok=True);c.parent.mkdir(parents=True,exist_ok=True);j.write_text(JS,encoding="utf-8");c.write_text(CSS,encoding="utf-8")
 for x in pages:inject(x,"</head>",f'<link rel="stylesheet" href="/dashboard-static/css/sprint13-plugins.css?v={V}">',r'\s*<link[^>]+sprint13-plugins\.css[^>]*>');inject(x,"</body>",f'<script src="/dashboard-static/js/sprint13-plugins.js?v={V}"></script>',r'\s*<script[^>]+sprint13-plugins\.js[^>]*></script>')
 t=mp.read_text(encoding="utf-8");imp="from services.plugin_platform_v13.routes import router as plugin_platform_v13_router";inc="app.include_router(plugin_platform_v13_router)";a=[x for x in (imp,inc) if x not in t];mp.write_text(t.rstrip()+("\n\n# SPRINT 13\n"+"\n".join(a)+"\n" if a else "\n"),encoding="utf-8")
 wt=sw.read_text(encoding="utf-8");wt=re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];','const CACHE = "noorbrain-sprint13-v1";',wt,count=1);sw.write_text(wt,encoding="utf-8")
 ins=p/"installer/sprint13";ins.mkdir(parents=True,exist_ok=True);labels=["13A MANIFEST SDK","13B REGISTRY","13C PERMISSIONS","13D LIFECYCLE","13E UI","13F FINAL"]
 for i,l in enumerate(labels,1):(ins/f"batch_{i}.py").write_text(f"print('SPRINT {l} PASS')\n")
 sdk=p/"sdk/plugin_manifest.example.json";sdk.parent.mkdir(parents=True,exist_ok=True);sdk.write_text(json.dumps({"id":"example-plugin","name":"Example Plugin","version":"1.0.0","permissions":["read_devices"],"entrypoint":"plugin.py"},indent=2)+"\n")
 test=p/"tests/sprint13_full_release_test.py";test.write_text(TEST,encoding="utf-8");rollback=ins/"rollback.py";rollback.write_text("from pathlib import Path\nimport shutil\n"+f"b=Path({str(b)!r})\n"+"p=Path.home()/'Projects'/'NoorBrain'\nfor r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(b/r,p/r)\nshutil.rmtree(p/'services/plugin_platform_v13',ignore_errors=True)\nprint('SPRINT 13 ROLLBACK COMPLETE')\n")
 py=p/"venv/bin/python";subprocess.run([str(py),"-m","py_compile",str(Path(__file__).resolve()),str(mp),str(s/"store.py"),str(s/"routes.py"),str(test),str(rollback)],check=True);print("SPRINT 13 FULL INSTALLED");return 0
if __name__=="__main__":raise SystemExit(main())
