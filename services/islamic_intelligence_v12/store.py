from __future__ import annotations
import json,threading
from datetime import datetime,timezone
import time
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
  with self.lock:d=self.read();r={"id":uuid4().hex,"name":p["name"],"event":p.get("event","person_entered"),"zone":p.get("zone",""),"message":p["message"],"enabled":bool(p.get("enabled",True)),"action_type":p.get("action_type","tts"),"media_id":p.get("media_id"),"target_node":p.get("target_node"),"cooldown_seconds":max(0,int(p.get("cooldown_seconds",1800))),"last_triggered":None,"created_at":self.now()};d["rules"].append(r);self.write(d);return r
 def patch_rule(self,i,p):
  with self.lock:d=self.read();r=next((x for x in d["rules"] if x["id"]==i),None)
  if r:
   for k in ("name","event","zone","message","enabled","action_type","media_id","target_node","cooldown_seconds"):
    if k in p:r[k]=p[k]
   self.write(d)
  return r
 def delete_rule(self,i):
  with self.lock:d=self.read();n=len(d["rules"]);d["rules"]=[x for x in d["rules"] if x["id"]!=i];ok=len(d["rules"])!=n
  if ok:self.write(d)
  return ok
 def evaluate(self,p):
  with self.lock:
   d=self.read();event=str(p.get("event") or "");zone=str(p.get("zone") or "");now=time.time();matches=[]
   for rule in d["rules"]:
    if not rule.get("enabled") or rule.get("event")!=event or (rule.get("zone") and str(rule.get("zone")).casefold()!=zone.casefold()):continue
    previous=float(rule.get("last_triggered_epoch") or 0);cooldown=max(0,int(rule.get("cooldown_seconds",1800)))
    if previous and now-previous<cooldown:continue
    matches.append(rule)
   executions=[]
   from services.playback_router import playback_router
   for rule in matches:
    try:
     routed=playback_router.play({"target_node":rule.get("target_node"),"type":rule.get("action_type") or ("media" if rule.get("media_id") else "tts"),"content":rule.get("message"),"media_id":rule.get("media_id")});executions.append({"rule_id":rule["id"],"status":"played","result":routed});rule["last_triggered"]=self.now();rule["last_triggered_epoch"]=now
    except Exception as error:executions.append({"rule_id":rule["id"],"status":"failed","error":str(error),"laptop_fallback":False})
   record={"id":uuid4().hex,"event":event,"zone":zone,"member_id":p.get("member_id"),"matches":[x["id"] for x in matches],"executions":executions,"at":self.now()};d["events"].append(record);d["events"]=d["events"][-1000:];self.write(d);return {"event":record,"reminders":matches,"executions":executions}
 def settings(self,p):
  with self.lock:d=self.read();d["settings"].update({k:v for k,v in p.items() if k in d["settings"]});self.write(d);return d["settings"]
store=Store()
