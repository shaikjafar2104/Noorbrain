from __future__ import annotations

import base64
import json
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

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


def _send_to_pi(file_path: Path, pi_url: str) -> None:
    try:
        body = json.dumps({
            "audio_base64": base64.b64encode(file_path.read_bytes()).decode("ascii"),
            "format": file_path.suffix.lstrip(".") or "mp3",
        }).encode("utf-8")
        request = urllib.request.Request(
            pi_url.rstrip("/") + "/play",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            response.read()
    except Exception:
        return


def play_media_rule(media_id: str) -> dict[str, Any]:
    item = media_library.get_item(media_id)
    file_path = media_library.get_file_path(media_id)
    config = _json(CONFIG, {})
    dual = _json(DUAL_CONFIG, {})
    app_enabled = bool(config.get("app_speaker", True))
    pi_enabled = bool(config.get("raspberry_pi_speaker", True))
    pi_url = str(dual.get("pi_node_url") or "http://192.168.2.29:8010")

    if app_enabled:
        _append_event(item)
    if pi_enabled:
        threading.Thread(target=_send_to_pi, args=(file_path, pi_url), daemon=True).start()

    return {
        "status": "routed",
        "player": (
            "app+raspberry_pi" if app_enabled and pi_enabled
            else "app" if app_enabled
            else "raspberry_pi" if pi_enabled
            else "disabled"
        ),
        "targets": {"app": app_enabled, "raspberry_pi": pi_enabled},
        "item": item,
    }
