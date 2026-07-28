from __future__ import annotations

import csv
import io
import json
from typing import Any


def export_json(events: list[dict[str, Any]]) -> bytes:
    return (
        json.dumps(
            {
                "status": "ok",
                "count": len(events),
                "events": events,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def export_csv(events: list[dict[str, Any]]) -> bytes:
    output = io.StringIO()
    fields = [
        "id",
        "created_at",
        "event_type",
        "source",
        "zone",
        "person_id",
        "confidence",
        "message",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()

    for event in events:
        writer.writerow({
            field: event.get(field)
            for field in fields
        })

    return output.getvalue().encode("utf-8")
