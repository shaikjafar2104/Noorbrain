"""Islamic Learning — JSON-backed store.

All religious CONTENT lives in questions.py (separate from UI logic).

This store only holds:
  - settings (enabled, kids_mode, voice_quiz, tts_voice, max_attempts)
  - user progress (quiz stats, mastered questions, child profiles)
  - categories (derived from questions module)

No religious content is invented here.

Testability: pass store_path= to use a temporary JSON file.
Production singleton keeps data/islamic_learning.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from .questions import DUAS, NAMES_99, SURAH_QUIZ, ARABIC_MATCH, ISLAMIC_KNOWLEDGE, KIDS_DATA

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = PROJECT_ROOT / "data" / "islamic_learning.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IslamicLearningStore:
    """Lightweight JSON store for Islamic Learning settings, progress, and categories."""

    def __init__(self, store_path: Path | None = None) -> None:
        self._store_path = store_path or STORE_PATH
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        if not self._store_path.is_file():
            self._write(self._default())

    def _default(self) -> dict[str, Any]:
        return {
            "version": "1.0.0",
            "settings": {
                "enabled": True,
                "kids_mode": False,
                "voice_quiz": False,
                "tts_voice": "default",
                "max_attempts_per_session": 10,
            },
            "categories": self._build_categories(),
            "quiz_stats": {
                "total_completed": 0,
                "average_score": 0.0,
                "total_correct": 0,
                "total_attempted": 0,
            },
            "mastered_questions": [],
            "child_profiles": [],
            "updated_at": utc_now_iso(),
        }

    @staticmethod
    def _build_categories() -> list[dict[str, Any]]:
        return [
            {
                "id": "dua-challenge",
                "name": "Dua Challenge",
                "description": "Learn and practice common supplications.",
                "question_count": len(DUAS),
                "icon": "🤲",
            },
            {
                "id": "names-99",
                "name": "99 Names of Allah",
                "description": "Learn the names and attributes of Allah.",
                "question_count": len(NAMES_99),
                "icon": "⭐",
            },
            {
                "id": "surah-quiz",
                "name": "Surah Quiz",
                "description": "Test your knowledge of Quranic chapters.",
                "question_count": len(SURAH_QUIZ),
                "icon": "📖",
            },
            {
                "id": "arabic-match",
                "name": "Arabic Match",
                "description": "Match Arabic phrases with English meanings.",
                "question_count": len(ARABIC_MATCH),
                "icon": "🔤",
            },
            {
                "id": "islamic-knowledge",
                "name": "Islamic Knowledge",
                "description": "Test basic Islamic knowledge.",
                "question_count": len(ISLAMIC_KNOWLEDGE),
                "icon": "🕌",
            },
            {
                "id": "family-quiz",
                "name": "Family Quiz",
                "description": "Family-friendly Islamic quiz combining multiple categories.",
                "question_count": len(SURAH_QUIZ) + len(ISLAMIC_KNOWLEDGE),
                "icon": "👨‍👩‍👧‍👦",
            },
            {
                "id": "kids-mode",
                "name": "Kids Mode",
                "description": "Simplified Islamic learning for children.",
                "question_count": len(KIDS_DATA["short_duas"]) + len(KIDS_DATA["colors_questions"]),
                "icon": "🧸",
            },
            {
                "id": "voice-quiz",
                "name": "Voice Quiz",
                "description": "Listen to questions and answer with your voice (where TTS is available).",
                "question_count": 5,
                "icon": "🎙️",
            },
        ]

    @property
    def store_path(self) -> Path:
        return self._store_path

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def _read_raw(self) -> dict[str, Any]:
        with self._lock:
            if not self._store_path.is_file():
                return self._default()
            try:
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return self._default()
            default = self._default()
            merged = dict(default)
            if isinstance(data, dict):
                for k in ("settings", "categories", "quiz_stats", "mastered_questions", "child_profiles"):
                    if k in data and isinstance(data[k], type(merged.get(k))):
                        merged[k] = data[k]
                merged["version"] = data.get("version", default["version"])
                merged["updated_at"] = data.get("updated_at", utc_now_iso())
            return merged

    def _write(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data["updated_at"] = utc_now_iso()
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._store_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            tmp.replace(self._store_path)
            return data

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def read(self) -> dict[str, Any]:
        return self._read_raw()

    def settings(self) -> dict[str, Any]:
        return self._read_raw().get("settings", {})

    def update_settings(self, changes: dict[str, Any]) -> dict[str, Any]:
        data = self._read_raw()
        settings = data.get("settings", {})
        settings.update({k: v for k, v in changes.items() if k in settings})
        data["settings"] = settings
        self._write(data)
        return settings

    def add_mastered_question(self, question_id: str) -> dict[str, Any]:
        data = self._read_raw()
        mastered = data.get("mastered_questions", [])
        if question_id not in mastered:
            mastered.append(question_id)
            data["mastered_questions"] = mastered
            self._write(data)
        return {"status": "ok", "mastered_count": len(mastered), "question_id": question_id}

    def record_quiz_result(self, correct: bool, total_this_session: int) -> dict[str, Any]:
        data = self._read_raw()
        stats = data.get("quiz_stats", {
            "total_completed": 0, "average_score": 0.0,
            "total_correct": 0, "total_attempted": 0,
        })
        stats["total_attempted"] = stats.get("total_attempted", 0) + 1
        if correct:
            stats["total_correct"] = stats.get("total_correct", 0) + 1
        total = stats.get("total_attempted", 0)
        stats["average_score"] = round(stats.get("total_correct", 0) / max(1, total), 3)
        if total_this_session > 0:
            stats["total_completed"] = stats.get("total_completed", 0) + 1
        data["quiz_stats"] = stats
        self._write(data)
        return {"status": "ok", "stats": stats}

    def get_quiz_stats(self) -> dict[str, Any]:
        return self._read_raw().get("quiz_stats", {
            "total_completed": 0, "average_score": 0.0,
            "total_correct": 0, "total_attempted": 0,
        })

    def add_child_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        data = self._read_raw()
        profiles = data.get("child_profiles", [])
        child_id = str(profile.get("child_id") or "").strip()
        if not child_id:
            child_id = hashlib.md5(json.dumps(profile, sort_keys=True).encode()).hexdigest()[:8]
            profile["child_id"] = child_id
        profiles.append(profile)
        data["child_profiles"] = profiles
        self._write(data)
        return {"status": "created", "child_id": child_id}

    def list_child_profiles(self) -> list[dict[str, Any]]:
        return self._read_raw().get("child_profiles", [])

    def delete_child_profile(self, child_id: str) -> dict[str, Any]:
        data = self._read_raw()
        profiles = data.get("child_profiles", [])
        before = len(profiles)
        profiles = [p for p in profiles if str(p.get("child_id", "")) != child_id]
        if len(profiles) == before:
            return {"status": "not_found", "child_id": child_id}
        data["child_profiles"] = profiles
        self._write(data)
        return {"status": "deleted", "child_id": child_id}


# Production singleton uses the default store path.
islamic_learning_store = IslamicLearningStore()
