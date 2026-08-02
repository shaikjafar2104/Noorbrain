import json,urllib.request
B="http://127.0.0.1:8001"
def c(p,m="GET",x=None):
 d=json.dumps(x).encode() if x is not None else None;h={"Content-Type":"application/json"} if d else {};q=urllib.request.Request(B+p,data=d,headers=h,method=m)
 with urllib.request.urlopen(q,timeout=30) as r:return json.loads(r.read().decode())
assert c("/api/dual-audio-v15/health")["version"]=="15.1.0"
x=c("/api/dual-audio-v15/config","PATCH",{"input_mode":"both","output_mode":"both","pi_node_url":"http://192.168.2.29:8010"})["config"];assert x["electronic_tts"] is False
with urllib.request.urlopen(B+"/mobile",timeout=30) as r:h=r.read().decode(errors="replace")
assert "dual-audio-v15.js?v=20260802-1" in h
print("ALL DUAL APP AND RASPBERRY PI AUDIO ROUTING TESTS PASSED")
