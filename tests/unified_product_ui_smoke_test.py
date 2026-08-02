from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


script = get("/dashboard-static/js/unified-product-ui.js?v=20260802-1")
assert "NoorBrainUnifiedUI" in script
assert "muteElectronicVoice" in script
assert "electronicVoice: \"disabled\"" in script
assert "nbPluginsV13" in script
assert "nbReleaseV14" in script
assert "nbWholeHomeV10" in script
assert "nbIslamicV12" in script

style = get("/dashboard-static/css/unified-product-ui.css?v=20260802-1")
assert ".nb-unified-hub" in style

for page in ("/studio", "/mobile"):
    html = get(page)
    assert "unified-product-ui.js?v=20260802-1" in html
    assert "unified-product-ui.css?v=20260802-1" in html

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-unified-product-ui-v1" in worker

config = get("/api/voice-platform-v9/config")
voice = json.loads(config)["config"]
assert voice["settings"]["startup_speech"] is False

print("ALL UNIFIED MOBILE WEB UI AND ELECTRONIC VOICE OFF TESTS PASSED")
