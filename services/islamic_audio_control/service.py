from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from services.media_library.media_manager import media_library
from services.playback_router import playback_router


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "data" / "islamic_audio_control.json"
DUAL_AUDIO_CONFIG = ROOT / "data" / "dual_audio_v15.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "version": "16.1.0",
    "output_mode": "pi",
    "target_node": None,
    "app_audio": False,
    "pi_audio": True,
    "electronic_tts": False,
    "morning": {"enabled": False, "time": "07:00", "query": "morning azkar"},
    "evening": {"enabled": False, "time": "18:00", "query": "evening azkar"},
}


class IslamicAudioControl:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._event: dict[str, Any] | None = None
        self._event_id = 0
        self._last_schedule_key = ""
        self._scheduler = threading.Thread(
            target=self._scheduler_loop,
            name="noorbrain-islamic-audio-scheduler",
            daemon=True,
        )
        self._scheduler.start()

    def read_config(self) -> dict[str, Any]:
        config = dict(DEFAULT_CONFIG)
        if DUAL_AUDIO_CONFIG.is_file():
            try:
                dual = json.loads(DUAL_AUDIO_CONFIG.read_text(encoding="utf-8"))
                for key in ("output_mode", "target_node", "app_audio", "pi_audio"):
                    if key in dual:
                        config[key] = dual[key]
            except Exception:
                pass
        if CONFIG_PATH.is_file():
            try:
                saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                config.update(saved)
            except Exception:
                pass
        config["electronic_tts"] = False
        return config

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = self.read_config()
        config["output_mode"] = "pi"
        config["app_audio"] = False
        if "target_node" in payload:
            config["target_node"] = str(payload.get("target_node") or "").strip() or None
        for period in ("morning", "evening"):
            incoming = payload.get(period)
            if isinstance(incoming, dict):
                current = dict(config.get(period) or {})
                if "enabled" in incoming:
                    current["enabled"] = bool(incoming["enabled"])
                if re.fullmatch(r"[0-2]\d:[0-5]\d", str(incoming.get("time", ""))):
                    current["time"] = str(incoming["time"])
                if str(incoming.get("query") or "").strip():
                    current["query"] = str(incoming["query"]).strip()[:150]
                config[period] = current
        config["electronic_tts"] = False
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return config

    @staticmethod
    def _search_text(item: dict[str, Any]) -> str:
        return " ".join(
            str(item.get(key) or "")
            for key in ("name", "original_filename", "stored_filename", "relative_path")
        ).casefold().replace("_", " ").replace("-", " ")

    def catalog(self, search: str = "") -> list[dict[str, Any]]:
        needle = " ".join(search.casefold().replace("_", " ").split())
        items = media_library.list_items(category="islamic")
        if needle:
            tokens = [x for x in re.findall(r"[a-z0-9]+", needle) if x not in {"play", "dua", "azkar", "the"}]
            items = [item for item in items if all(token in self._search_text(item) for token in tokens)]
        return items

    def find(self, query: str) -> dict[str, Any]:
        clean = query.casefold()
        clean = re.sub(r"\b(hey|noor|please|play|chalao|sunao|suna|do|dua|azkar|audio)\b", " ", clean)
        clean = " ".join(re.findall(r"[a-z0-9]+", clean))
        items = media_library.list_items(category="islamic")
        if not items:
            raise LookupError("Islamic audio library is empty.")
        if not clean:
            return items[0]
        tokens = clean.split()
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in items:
            haystack = self._search_text(item)
            score = sum(4 for token in tokens if token in haystack)
            if clean in haystack:
                score += 20
            if score:
                scored.append((score, item))
        if not scored:
            raise LookupError(f"No Islamic audio matched: {query}")
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[0][1]

    def play_item(self, media_id: str, source: str = "manual", target_node: str | None = None) -> dict[str, Any]:
        item = media_library.get_item(media_id)
        config = self.read_config()
        selected_target = str(target_node or config.get("target_node") or "").strip()
        routed = playback_router.play({"target_node": selected_target, "type": "media", "media_id": media_id})
        with self._lock:
            self._event_id += 1
            self._event = {
                "id": self._event_id,
                "created_at": datetime.now().isoformat(),
                "source": source,
                "item": item,
                "target_node": selected_target,
                "playback": routed,
            }
        return {
            "status": "playing",
            "reply": f"Playing {item.get('name') or item.get('original_filename')}.",
            "item": item,
            "output_mode": "pi",
            "target_node": selected_target,
            "playback": routed,
            "app": None,
            "event_id": self._event_id,
        }

    def play_by_query(self, query: str, source: str = "voice", target_node: str | None = None) -> dict[str, Any]:
        return self.play_item(str(self.find(query)["id"]), source=source, target_node=target_node)

    def event_after(self, event_id: int) -> dict[str, Any] | None:
        with self._lock:
            if self._event is None or int(self._event["id"]) <= event_id:
                return None
            return dict(self._event)

    def _scheduler_loop(self) -> None:
        while True:
            try:
                now = datetime.now()
                hhmm = now.strftime("%H:%M")
                config = self.read_config()
                for period in ("morning", "evening"):
                    rule = config.get(period) or {}
                    key = f"{now.date()}:{period}:{hhmm}"
                    if rule.get("enabled") and rule.get("time") == hhmm and key != self._last_schedule_key:
                        self._last_schedule_key = key
                        self.play_by_query(str(rule.get("query") or period + " azkar"), source="schedule")
            except Exception:
                pass
            time.sleep(20)


islamic_audio = IslamicAudioControl()
