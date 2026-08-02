from __future__ import annotations
import json,urllib.request
BASE="http://127.0.0.1:8001"
def api(path):
 with urllib.request.urlopen(BASE+path,timeout=60) as response:return json.loads(response.read().decode())
checks=[
 ("/api/sprint8-release/health","8.6.0"),
 ("/api/universal-voice-v9/health","9.1.0"),
 ("/api/voice-platform-v9/health","9.6.0"),
 ("/api/whole-home-v10/health","10.0.0"),
 ("/api/family-intelligence-v11/health","11.0.0"),
 ("/api/islamic-intelligence-v12/health","12.0.0"),
 ("/api/plugin-platform-v13/health","13.0.0"),
 ("/api/platform-release-v14/health","14.0.0"),
]
for path,version in checks:
 result=api(path);assert result["version"]==version,(path,result);print("PASS",path)
audit=api("/api/platform-release-v14/audit");assert audit["status"]=="production";assert audit["ready"]==audit["total"]
release=api("/api/platform-release-v14/release")["release"];assert release["status"]=="production";assert release["version"]=="14.0.0"
for page in ("/studio","/mobile"):
 with urllib.request.urlopen(BASE+page,timeout=30) as response:html=response.read().decode(errors="replace")
 assert "sprint14-release.js?v=20260802-1" in html
with urllib.request.urlopen(BASE+"/dashboard-pwa/sw.js",timeout=30) as response:worker=response.read().decode(errors="replace")
assert "noorbrain-production-v14" in worker
print("ALL NOORBRAIN SPRINT 8-14 PRODUCTION RELEASE TESTS PASSED")
