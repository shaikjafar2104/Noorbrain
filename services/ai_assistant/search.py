from __future__ import annotations

import math
import re
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Iterable

STOP_WORDS = {
    "a", "an", "and", "are", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "me", "my", "of", "on", "or", "show", "that",
    "the", "this", "to", "what", "when", "where", "who", "with",
    "hai", "ka", "ki", "ke", "ko", "mein", "mujhe", "dikhao", "batao",
}

TIME_PATTERNS = (
    (re.compile(r"\b(today|aaj)\b", re.I), 1),
    (re.compile(r"\b(yesterday|kal)\b", re.I), 2),
    (re.compile(r"\b(last\s+week|pichle\s+hafte)\b", re.I), 7),
    (re.compile(r"\b(last\s+month|pichle\s+mahine)\b", re.I), 30),
)

KIND_ALIASES = {
    "event": {"event", "activity", "movement", "detection"},
    "habit": {"habit", "routine", "pattern"},
    "person": {"person", "people", "visitor", "face"},
    "reminder": {"reminder", "dua", "azkar", "alert"},
    "note": {"note", "memory", "remember"},
}


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9_'-]+", (text or "").lower())
        if len(token) > 1 and token not in STOP_WORDS
    ]


def infer_filters(query: str) -> dict[str, Any]:
    text = (query or "").strip()
    lowered = text.lower()
    filters: dict[str, Any] = {}

    for pattern, days in TIME_PATTERNS:
        if pattern.search(text):
            now = datetime.now()
            if days == 1:
                start = datetime(now.year, now.month, now.day)
            elif days == 2:
                start = datetime(now.year, now.month, now.day) - timedelta(days=1)
                filters["created_before"] = start.timestamp() + 86400
            else:
                start = now - timedelta(days=days)
            filters["created_after"] = start.timestamp()
            break

    for kind, aliases in KIND_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}s?\b", lowered) for alias in aliases):
            filters["kind"] = kind
            break

    zone_match = re.search(r"\b(?:zone|room|area)\s*[:=]?\s*([\w -]{2,40})", text, re.I)
    if zone_match:
        filters["zone_hint"] = zone_match.group(1).strip(" .,?!")

    person_match = re.search(r"\b(?:person|for|about)\s*[:=]?\s*([A-Z][\w'-]{1,40})", text)
    if person_match:
        filters["person_hint"] = person_match.group(1)

    return filters


def _age_score(created_at: float, now: float) -> float:
    age_days = max(0.0, (now - float(created_at or now)) / 86400.0)
    return math.exp(-age_days / 30.0)


def rank_memories(
    memories: Iterable[dict[str, Any]],
    query: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    query_tokens = tokenize(query)
    query_counts = Counter(query_tokens)
    inferred = infer_filters(query)
    now = time.time()
    ranked: list[dict[str, Any]] = []

    for memory in memories:
        created_at = float(memory.get("created_at") or now)
        if inferred.get("created_after") and created_at < inferred["created_after"]:
            continue
        if inferred.get("created_before") and created_at >= inferred["created_before"]:
            continue

        kind = str(memory.get("kind") or "").lower()
        if inferred.get("kind") and inferred["kind"] not in kind:
            # Keep weak matches rather than making natural-language filters brittle.
            kind_penalty = 0.15
        else:
            kind_penalty = 1.0

        searchable = " ".join(
            str(memory.get(field) or "")
            for field in ("title", "content", "kind", "person_id", "zone", "source")
        ).lower()
        document_counts = Counter(tokenize(searchable))
        overlap = sum(min(count, document_counts[token]) for token, count in query_counts.items())
        coverage = overlap / max(1, sum(query_counts.values()))

        phrase_bonus = 0.0
        normalized_query = " ".join(query_tokens)
        if normalized_query and normalized_query in searchable:
            phrase_bonus = 0.35

        zone_hint = str(inferred.get("zone_hint") or "").lower()
        person_hint = str(inferred.get("person_hint") or "").lower()
        scope_bonus = 0.0
        if zone_hint and zone_hint in str(memory.get("zone") or "").lower():
            scope_bonus += 0.35
        if person_hint and person_hint in str(memory.get("person_id") or "").lower():
            scope_bonus += 0.35

        importance = max(0.0, min(1.0, float(memory.get("importance") or 0.5)))
        recency = _age_score(created_at, now)
        score = kind_penalty * (
            coverage * 0.55
            + phrase_bonus
            + scope_bonus
            + importance * 0.20
            + recency * 0.25
        )

        if query_tokens and overlap == 0 and scope_bonus == 0 and phrase_bonus == 0:
            continue

        item = dict(memory)
        item["relevance_score"] = round(score, 4)
        item["matched_terms"] = sorted(set(query_tokens) & set(document_counts))
        ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item.get("relevance_score", 0.0),
            item.get("importance", 0.0),
            item.get("created_at", 0.0),
        ),
        reverse=True,
    )
    return ranked[: max(1, min(int(limit), 100))]
