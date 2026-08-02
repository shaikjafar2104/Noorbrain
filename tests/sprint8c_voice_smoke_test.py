from __future__ import annotations

import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    script = get(
        "/dashboard-static/js/"
        "sprint8c-voice-repeat-guard.js?v=20260731-1"
    )
    assert "NoorBrainVoiceRepeatGuard" in script
    assert "SAME_REPLY_WINDOW_MS = 12000" in script
    assert "noorbrain:voice-duplicate-blocked" in script

    mobile = get("/mobile")
    assert "sprint8c-voice-repeat-guard.js?v=20260731-1" in mobile

    studio = get("/studio")
    assert "sprint8c-voice-repeat-guard.js?v=20260731-1" in studio

    sw = get("/dashboard-pwa/sw.js")
    assert "noorbrain-sprint8c-voice-stability-v1" in sw

    print("ALL SPRINT 8C VOICE STABILITY TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
