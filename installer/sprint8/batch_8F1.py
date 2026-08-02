from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


project = Path(__file__).resolve().parents[2]
memory = project / "data" / "halo_conversation_memory_v8.json"
if memory.is_file():
    data = json.loads(memory.read_text(encoding="utf-8"))
    data.setdefault("version", "8.4.0")
    data.setdefault("sessions", {})
    data["migrated_at"] = datetime.now(timezone.utc).isoformat()
    memory.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
print("SPRINT 8F.1 DATA MIGRATION PASS")
