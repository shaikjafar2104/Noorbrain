from __future__ import annotations

import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


script = get(
    "/dashboard-static/js/production-ui-cleanup.js?v=20260802-1"
)
assert "NoorBrainProductionCleanup" in script
assert "stale-duplicate-camera" in script
assert "developer-sprint-label" in script
assert "smoke-test-activity" in script
assert "Camera & Vision Product" in script

style = get(
    "/dashboard-static/css/production-ui-cleanup.css?v=20260802-1"
)
assert ".nb-production-hidden" in style

for page in ("/studio", "/mobile"):
    html = get(page)
    assert "production-ui-cleanup.js?v=20260802-1" in html
    assert "production-ui-cleanup.css?v=20260802-1" in html

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-production-ui-cleanup-v1" in worker
assert "production-ui-cleanup.js?v=20260802-1" in worker

print("ALL NOORBRAIN PRODUCTION UI CLEANUP TESTS PASSED")
