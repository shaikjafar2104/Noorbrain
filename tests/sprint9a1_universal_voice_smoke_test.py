from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def call(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


health = call("/api/universal-voice-v9/health")
assert health["version"] == "9.1.0"

capabilities = call("/api/universal-voice-v9/capabilities")
assert capabilities["duplicate_protection"] is True
assert capabilities["conversation_context"] is True

first = call(
    "/api/universal-voice-v9/prepare", "POST",
    {"session_id": "sprint9a1-smoke", "transcript": "Turn on the Hall light."},
)
assert first["accepted"] is True
assert "context" in first

second = call(
    "/api/universal-voice-v9/prepare", "POST",
    {"session_id": "sprint9a1-smoke", "transcript": "Turn on the Hall light."},
)
assert second["duplicate"] is True

with urllib.request.urlopen(
    BASE + "/dashboard-static/js/sprint9a1-universal-voice.js?v=20260801-1",
    timeout=30,
) as response:
    script = response.read().decode("utf-8", errors="replace")
assert "NoorBrainUniversalVoice" in script

for page in ("/studio", "/mobile"):
    with urllib.request.urlopen(BASE + page, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    assert "sprint9a1-universal-voice.js?v=20260801-1" in html

print("ALL SPRINT 9A.1 UNIVERSAL VOICE GATEWAY TESTS PASSED")
