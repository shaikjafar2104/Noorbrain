from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from services.playback_router import playback_router
from services.media_library.media_manager import media_library


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data" / "audio_camera_rules_v15.json"
DUAL_CONFIG = ROOT / "data" / "dual_audio_v15.json"
EVENTS = ROOT / "data" / "islamic_audio_events.json"


def _json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _append_event(item: dict[str, Any]) -> None:
    rows = _json(EVENTS, [])
    if not isinstance(rows, list):
        rows = []
    rows.append({
        "event_id": uuid.uuid4().hex,
        "timestamp": time.time(),
        "media_id": item["id"],
        "name": item.get("name") or item.get("original_filename"),
        "file_url": item.get("file_url") or f"/media/{item['id']}/file",
    })
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    EVENTS.write_text(json.dumps(rows[-100:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def play_media_rule(media_id: str, target_node: str) -> dict[str, Any]:
    item = media_library.get_item(media_id)
    result = playback_router.play({"target_node": target_node, "type": "media", "media_id": media_id})
    _append_event(item)
    return {**result, "item": item, "player": "raspberry_pi", "targets": {"app": False, "raspberry_pi": True}}
