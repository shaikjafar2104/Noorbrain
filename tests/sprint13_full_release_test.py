import json,urllib.request
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
