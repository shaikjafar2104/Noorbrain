from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def call(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


health = call("/api/halo-decision-v8/health")
assert health["version"] == "8.1.0"

state = call("/api/halo-decision-v8/state")
assert "decision_engine" in state

print("ALL SPRINT 8A.1 TESTS PASSED")
