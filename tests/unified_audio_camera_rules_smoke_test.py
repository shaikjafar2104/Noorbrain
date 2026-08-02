import json,urllib.request
B="http://127.0.0.1:8001"
def c(p,m="GET",x=None):
 d=json.dumps(x).encode() if x is not None else None;h={"Content-Type":"application/json"} if d else {};q=urllib.request.Request(B+p,data=d,headers=h,method=m)
 with urllib.request.urlopen(q,timeout=30) as r:return json.loads(r.read().decode())
assert c("/api/audio-camera-rules-v15/health")["version"]=="15.2.0"
x=c("/api/audio-camera-rules-v15/config","PATCH",{"camera_triggered_audio":True,"raspberry_pi_speaker":True,"app_speaker":True,"adhan_media_audio":True})["config"]
assert x["single_camera_mode"] is True and x["electronic_robotic_voice"] is False and x["output_mode"]=="both"
e=c("/api/audio-camera-rules-v15/evaluate-camera-event","POST",{"rule_matched":True});assert e["targets"]==["raspberry_pi","app"] and e["electronic_voice"] is False
for p in ("/studio","/mobile"):
 with urllib.request.urlopen(B+p,timeout=30) as r:h=r.read().decode(errors="replace")
 assert "unified-audio-camera-rules.js?v=20260802-1" in h
print("ALL UNIFIED AUDIO AND CAMERA RULES TESTS PASSED")
