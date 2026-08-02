from __future__ import annotations
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
