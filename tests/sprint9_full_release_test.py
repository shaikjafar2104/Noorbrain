from __future__ import annotations
import json
import urllib.request

BASE="http://127.0.0.1:8001"
def call(path,method="GET",payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    headers={"Content-Type":"application/json"} if data else {}
    request=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=30) as response:
        return json.loads(response.read().decode())

assert call("/api/universal-voice-v9/health")["version"]=="9.1.0"
assert call("/api/voice-platform-v9/health")["version"]=="9.6.0"
config=call("/api/voice-platform-v9/config")["config"]
assert len(config["profiles"])>=3
selected=call("/api/voice-platform-v9/profiles/halo-calm/select","POST")
assert selected["config"]["selected_profile"]=="halo-calm"
updated=call("/api/voice-platform-v9/config","PATCH",{"startup_speech":False,"speech_rate":1.0})
assert updated["config"]["settings"]["startup_speech"] is False
session=call("/api/voice-platform-v9/sessions/start","POST",{"source":"smoke"})["session"]
assert call(f"/api/voice-platform-v9/sessions/{session['id']}/end","POST")["status"]=="ended"
for page in ("/studio","/mobile"):
    with urllib.request.urlopen(BASE+page,timeout=30) as response: html=response.read().decode(errors="replace")
    assert "sprint9-voice-platform.js?v=20260801-1" in html
with urllib.request.urlopen(BASE+"/dashboard-pwa/sw.js",timeout=30) as response: sw=response.read().decode(errors="replace")
assert "noorbrain-sprint9-voice-platform-final-v1" in sw
print("ALL SPRINT 9 VOICE PLATFORM PRODUCTION TESTS PASSED")
