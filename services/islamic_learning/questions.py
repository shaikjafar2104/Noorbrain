"""
Islamic Learning — content module.

All religious content MUST be sourced from existing verified NoorBrain
Islamic content/media/manifests. No newly-authored religious material.

Mixed-language category labels, unverified Arabic/transliteration pairs,
and fabricated source references are NOT included.

If verified project content is insufficient for a category, that category
returns an empty/limited dataset and the framework exposes
VERIFIED_CONTENT_REQUIRED = True.
"""
from __future__ import annotations

from typing import Any

VERIFIED_CONTENT_REQUIRED = True

# ------------------------------------------------------------------
# Dua Challenge — empty until verified project content is available
# ------------------------------------------------------------------

DUAS: list[dict[str, Any]] = []

# ------------------------------------------------------------------
# 99 Names of Allah — empty until verified project content is available
# ------------------------------------------------------------------

NAMES_99: list[dict[str, Any]] = []

# ------------------------------------------------------------------
# Surah Quiz — empty until verified project content is available
# ------------------------------------------------------------------

SURAH_QUIZ: list[dict[str, Any]] = []

# ------------------------------------------------------------------
# Arabic Match — empty until verified project content is available
# ------------------------------------------------------------------

ARABIC_MATCH: list[dict[str, Any]] = []

# ------------------------------------------------------------------
# Islamic Knowledge — empty until verified project content is available
# ------------------------------------------------------------------

ISLAMIC_KNOWLEDGE: list[dict[str, Any]] = []

# ------------------------------------------------------------------
# Kids Mode — empty until verified project content is available
# ------------------------------------------------------------------

KIDS_DATA: dict[str, Any] = {
    "short_duas": [],
    "colors_questions": [],
}
