from __future__ import annotations

from typing import Any

from .store import halo_brain_store


class HALOMemoryEngine:
    def remember(
        self,
        *,
        kind: str,
        value: Any,
        person_id: str | None,
        zone: str | None,
        importance: float,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return halo_brain_store.add("memories", {
            "kind": kind,
            "value": value,
            "person_id": person_id,
            "zone": zone,
            "importance": importance,
            "metadata": metadata,
        })

    def recall(
        self,
        *,
        query: str | None = None,
        person_id: str | None = None,
        zone: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        memories = halo_brain_store.list("memories", limit=5000)
        result = []
        query_fold = query.casefold() if query else None

        for memory in memories:
            if person_id and memory.get("person_id") != person_id:
                continue

            if zone and str(memory.get("zone") or "").casefold() != zone.casefold():
                continue

            if query_fold:
                haystack = " ".join([
                    str(memory.get("kind") or ""),
                    str(memory.get("value") or ""),
                    str(memory.get("zone") or ""),
                    str(memory.get("person_id") or ""),
                ]).casefold()

                if query_fold not in haystack:
                    continue

            result.append(memory)

            if len(result) >= limit:
                break

        return result


halo_memory_engine = HALOMemoryEngine()
