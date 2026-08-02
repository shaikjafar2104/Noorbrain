from __future__ import annotations
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
