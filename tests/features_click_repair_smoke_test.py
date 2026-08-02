from __future__ import annotations

import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


script = get(
    "/dashboard-static/js/features-click-repair.js?v=20260802-2"
)
assert "NoorBrainFeatureClickRepair" in script
assert "data-nb-feature" in script
assert "touchend" in script
assert "stopImmediatePropagation" in script
assert "nbWholeHomeV10" in script
assert "nbFamilyV11" in script
assert "nbIslamicV12" in script

style = get(
    "/dashboard-static/css/features-click-repair.css?v=20260802-2"
)
assert "touch-action: manipulation" in style

for page in ("/studio", "/mobile"):
    html = get(page)
    assert "features-click-repair.js?v=20260802-2" in html
    assert "features-click-repair.css?v=20260802-2" in html

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-features-click-repair-v2" in worker

print("ALL NOORBRAIN FEATURES CLICK REPAIR TESTS PASSED")
