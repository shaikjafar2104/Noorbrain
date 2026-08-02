from __future__ import annotations

import urllib.request


URL = (
    "http://127.0.0.1:8001/dashboard-static/js/"
    "sprint8c-voice-repeat-guard.js?v=20260801-2"
)


with urllib.request.urlopen(URL, timeout=30) as response:
    script = response.read().decode("utf-8", errors="replace")

assert "bootMuteUntil: Date.now() + 8000" in script
assert "userActivated: false" in script
assert "cancelStartupVoice" in script
assert "activateVoiceFromUser" in script
assert "event?.isTrusted === false" in script

print("ALL SPRINT 8C.2 STARTUP VOICE SILENCE TESTS PASSED")
