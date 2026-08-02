from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> tuple[str, str]:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return response.headers.get("content-type", ""), response.read().decode(
            "utf-8", errors="replace"
        )


_, raw = get("/api/ai-control-center-v8/health")
health = json.loads(raw)
assert health["version"] == "8.5.0"

_, raw = get("/api/ai-control-center-v8/overview")
overview = json.loads(raw)
assert "conversation_memory" in overview
assert "voice_context" in overview
assert "routine_intelligence" in overview

_, script = get("/dashboard-static/js/sprint8e1-ai-dashboard.js?v=20260801-1")
assert "NoorBrainAIControlCenter" in script

_, style = get("/dashboard-static/css/sprint8e1-ai-dashboard.css?v=20260801-1")
assert ".nb-ai-center" in style

_, studio = get("/studio")
assert "sprint8e1-ai-dashboard.js?v=20260801-1" in studio
assert "sprint8e1-ai-dashboard.css?v=20260801-1" in studio

print("ALL SPRINT 8E.1 AI DASHBOARD TESTS PASSED")
