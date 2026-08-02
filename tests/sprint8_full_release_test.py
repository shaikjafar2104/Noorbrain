from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> tuple[int, str]:
    with urllib.request.urlopen(BASE + path, timeout=60) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def api(path: str) -> dict:
    status, raw = get(path)
    assert status == 200, path
    return json.loads(raw)


status, _ = get("/health")
assert status == 200
print("PASS NoorBrain core health")

routine = api("/api/routine-intelligence-v8/health")
assert routine["version"] == "8.2.0"
print("PASS Sprint 8B routine intelligence")

memory = api("/api/halo-memory-v8/health")
assert memory["version"] == "8.4.0"
print("PASS Sprint 8D.1 conversation memory")

voice = api("/api/halo-voice-context-v8/health")
assert voice["version"] == "8.4.1"
print("PASS Sprint 8D.2 voice context")

center = api("/api/ai-control-center-v8/health")
assert center["version"] == "8.5.0"
print("PASS Sprint 8E.1 AI dashboard API")

overview = api("/api/ai-control-center-v8/overview")
assert "conversation_memory" in overview
assert "routine_intelligence" in overview
print("PASS AI overview integration")

release = api("/api/sprint8-release/health")
assert release["version"] == "8.6.0"
assert release["status"] == "healthy"
print("PASS Sprint 8 production release health")

release_status = api("/api/sprint8-release/status")
assert release_status["status"] == "production"
assert release_status["installed_components"] == release_status["total_components"]
print("PASS all Sprint 8 components installed")

_, studio = get("/studio")
assert "sprint8e1-ai-dashboard.js" in studio
print("PASS AI Studio integration")

_, mobile = get("/mobile")
assert "sprint8e2-mobile-ai.js" in mobile
assert "sprint8c-voice-repeat-guard.js" in mobile
print("PASS Mobile AI and voice stability integration")

_, worker = get("/dashboard-pwa/sw.js")
assert "sprint8e2-mobile-ai.js" in worker
print("PASS production PWA assets")

print("ALL SPRINT 8 PRODUCTION RELEASE TESTS PASSED")
