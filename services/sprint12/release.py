from __future__ import annotations

from pathlib import Path
from typing import Any

from .final_qa import sprint12_final_qa


class Sprint12Release:
    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.marker = self.project_root / "data" / "sprint12_release.json"

    def status(self) -> dict[str, Any]:
        qa = sprint12_final_qa.run()
        return {
            "status": "ready" if qa["status"] == "PASS" else "blocked",
            "release": "NoorBrain v1.0 RC",
            "sprint": "12",
            "packs": {
                "pack1": "complete",
                "pack2": "complete",
                "pack3": "complete",
                "pack4": "complete",
                "pack5": "complete" if qa["status"] == "PASS" else "qa_failed",
            },
            "qa": qa,
            "ready_for_v1": qa["status"] == "PASS",
        }

    def mark(self) -> dict[str, Any]:
        import json
        from datetime import datetime, timezone

        payload = self.status()
        payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        self.marker.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return payload


sprint12_release = Sprint12Release()
