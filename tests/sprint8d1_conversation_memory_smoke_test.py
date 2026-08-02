from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001/api/halo-memory-v8"
SESSION = "sprint8d1-smoke"


def call(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        BASE + path,
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


health = call("/health")
assert health["version"] == "8.4.0"

call(f"/sessions/{SESSION}", "DELETE")

remembered = call(
    f"/sessions/{SESSION}/remember",
    "POST",
    {"role": "user", "text": "My preferred room is Hall."},
)
assert remembered["status"] == "remembered"

facts = call(
    f"/sessions/{SESSION}/facts/preferred_room",
    "PUT",
    {"value": "Hall"},
)
assert facts["facts"]["preferred_room"] == "Hall"

context = call(f"/sessions/{SESSION}/context?limit=10")
assert context["session"]["messages"][-1]["text"] == "My preferred room is Hall."
assert context["session"]["facts"]["preferred_room"] == "Hall"

cleared = call(f"/sessions/{SESSION}", "DELETE")
assert cleared["removed"] is True

print("ALL SPRINT 8D.1 HALO CONVERSATION MEMORY TESTS PASSED")
