from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"
SESSION = "sprint8d2-smoke"


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


health = call("/api/halo-voice-context-v8/health")
assert health["version"] == "8.4.1"

call(f"/api/halo-memory-v8/sessions/{SESSION}", "DELETE")

exchange = call(
    "/api/halo-voice-context-v8/exchange",
    "POST",
    {
        "session_id": SESSION,
        "user_text": "Turn on the Hall light.",
        "assistant_text": "The Hall light is on.",
    },
)
assert exchange["status"] == "remembered"

context = call(
    "/api/halo-voice-context-v8/context",
    "POST",
    {
        "session_id": SESSION,
        "utterance": "Turn it off.",
    },
)
assert context["context"]["message_count"] == 2
assert context["context"]["recent_messages"][-1]["role"] == "assistant"
assert context["context"]["utterance"] == "Turn it off."

call(f"/api/halo-memory-v8/sessions/{SESSION}", "DELETE")
print("ALL SPRINT 8D.2 HALO VOICE CONTEXT TESTS PASSED")
