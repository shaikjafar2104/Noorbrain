from __future__ import annotations
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
