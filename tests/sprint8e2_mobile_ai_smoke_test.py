from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


overview = json.loads(get("/api/ai-control-center-v8/overview"))
assert overview["version"] == "8.5.0"

script = get("/dashboard-static/js/sprint8e2-mobile-ai.js?v=20260801-1")
assert "NoorBrainMobileAI" in script
assert "nbMobileAiCenterV8" in script

style = get("/dashboard-static/css/sprint8e2-mobile-ai.css?v=20260801-1")
assert ".nb-mobile-ai" in style

mobile = get("/mobile")
assert "sprint8e2-mobile-ai.js?v=20260801-1" in mobile
assert "sprint8e2-mobile-ai.css?v=20260801-1" in mobile

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-sprint8e2-mobile-ai-v1" in worker
assert "/dashboard-static/js/sprint8e2-mobile-ai.js?v=20260801-1" in worker

print("ALL SPRINT 8E.2 MOBILE AI CONTROL CENTER TESTS PASSED")
