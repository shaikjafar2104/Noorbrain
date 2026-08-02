import json,urllib.request
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
