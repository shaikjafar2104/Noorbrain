from __future__ import annotations

import json
from pathlib import Path


project = Path(__file__).resolve().parents[2]
manifest = project / "data" / "sprint8_release.json"
data = json.loads(manifest.read_text(encoding="utf-8"))
assert data["status"] == "production"
assert data["version"] == "8.6.0"
print("SPRINT 8F.2 PRODUCTION FINALIZATION PASS")
