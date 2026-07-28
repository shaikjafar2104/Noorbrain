from __future__ import annotations

import time
from collections import Counter
from datetime import datetime
from typing import Any

from services.ai_memory.store import MemoryStore
from .search import infer_filters, rank_memories


class LocalAssistant:
    """Private, deterministic assistant that works without cloud APIs."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.started_at = time.time()
        self.request_count = 0

    def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        self.request_count += 1
        # Fetch a broad candidate set, then apply natural-language ranking locally.
        candidates = self.store.list(limit=500, include_expired=False)
        results = rank_memories(candidates, query, limit=limit)
        return {
            "query": query,
            "filters": infer_filters(query),
            "count": len(results),
            "results": results,
        }

    @staticmethod
    def _format_memory(memory: dict[str, Any]) -> str:
        created = datetime.fromtimestamp(float(memory.get("created_at") or time.time()))
        scope = []
        if memory.get("person_id"):
            scope.append(f"person {memory['person_id']}")
        if memory.get("zone"):
            scope.append(f"zone {memory['zone']}")
        suffix = f" ({', '.join(scope)})" if scope else ""
        return f"{created:%Y-%m-%d %H:%M} — {memory.get('title', 'Memory')}{suffix}: {memory.get('content', '')}"

    def answer(self, message: str, limit: int = 8) -> dict[str, Any]:
        search_result = self.search(message, limit=limit)
        memories = search_result["results"]

        if not memories:
            answer = (
                "Mujhe is sawal se related koi saved memory nahi mili. "
                "Aap memory add karke dobara pooch sakte hain."
            )
        else:
            lines = [self._format_memory(item) for item in memories[:5]]
            answer = "NoorBrain memory ke mutabiq:\n" + "\n".join(
                f"{index}. {line}" for index, line in enumerate(lines, start=1)
            )

        return {
            "status": "ok",
            "mode": "local-memory-assistant",
            "message": message,
            "answer": answer,
            "evidence_count": len(memories),
            "evidence": memories,
            "filters": search_result["filters"],
        }

    def insights(self, limit: int = 10) -> dict[str, Any]:
        memories = self.store.list(limit=500, include_expired=False)
        kind_counts = Counter(str(item.get("kind") or "unknown") for item in memories)
        zone_counts = Counter(str(item.get("zone")) for item in memories if item.get("zone"))
        person_counts = Counter(
            str(item.get("person_id")) for item in memories if item.get("person_id")
        )
        recent = sorted(memories, key=lambda item: item.get("created_at", 0), reverse=True)[:limit]

        return {
            "generated_at": time.time(),
            "total_active_memories": len(memories),
            "top_kinds": kind_counts.most_common(limit),
            "top_zones": zone_counts.most_common(limit),
            "top_people": person_counts.most_common(limit),
            "recent_memories": recent,
            "assistant_requests": self.request_count,
            "uptime_seconds": round(time.time() - self.started_at, 2),
        }
