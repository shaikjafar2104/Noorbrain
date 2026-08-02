import json,urllib.request
BASE="http://127.0.0.1:8001"
def call(path,method="GET",payload=None):
    body=None; headers={"Accept":"application/json"}
    if payload is not None:body=json.dumps(payload).encode(); headers["Content-Type"]="application/json"
    req=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
health=call("/api/routine-intelligence-v8/health"); assert health["version"]=="8.2.0"
activity=call("/api/routine-intelligence-v8/activities","POST",{"name":"Smoke Activity","category":"test","room":"hall"})["activity"]
timeline=call("/api/routine-intelligence-v8/timeline?days=1"); assert any(x["id"]==activity["id"] for x in timeline["activities"])
call("/api/routine-intelligence-v8/habits/detect","POST",{})
call("/api/routine-intelligence-v8/predict","POST",{})
print("ALL SPRINT 8B TESTS PASSED")
