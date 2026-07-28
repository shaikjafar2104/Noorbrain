from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FaceIdentityStore:
    def __init__(self) -> None:
        project = Path(__file__).resolve().parents[2]
        self.path = project / "data" / "face_identity.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        if not self.path.exists():
            self._write({
                "schema_version": 1,
                "persons": [],
                "samples": [],
                "recognition_events": [],
            })

    def _read(self) -> dict[str, Any]:
        with self._lock:
            payload = json.loads(self.path.read_text(encoding="utf-8"))

        payload.setdefault("schema_version", 1)
        payload.setdefault("persons", [])
        payload.setdefault("samples", [])
        payload.setdefault("recognition_events", [])
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            fd, temp_name = tempfile.mkstemp(
                prefix="face-identity-",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(
                        payload,
                        handle,
                        indent=2,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def create_person(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()
        person = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "active": True,
            **item,
        }
        payload["persons"].append(person)
        self._write(payload)
        return person

    def list_persons(self) -> list[dict[str, Any]]:
        payload = self._read()
        persons = []

        for person in payload["persons"]:
            sample_count = sum(
                1
                for sample in payload["samples"]
                if sample.get("person_id") == person.get("id")
            )
            persons.append({
                **person,
                "sample_count": sample_count,
            })

        return sorted(
            persons,
            key=lambda item: str(item.get("name", "")).casefold(),
        )

    def get_person(self, person_id: str) -> dict[str, Any] | None:
        return next(
            (
                person
                for person in self._read()["persons"]
                if person.get("id") == person_id
            ),
            None,
        )

    def delete_person(self, person_id: str) -> int:
        payload = self._read()
        before = len(payload["persons"])
        payload["persons"] = [
            person
            for person in payload["persons"]
            if person.get("id") != person_id
        ]
        payload["samples"] = [
            sample
            for sample in payload["samples"]
            if sample.get("person_id") != person_id
        ]
        removed = before - len(payload["persons"])
        self._write(payload)
        return removed

    def add_sample(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()
        sample = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            **item,
        }
        payload["samples"].append(sample)
        payload["samples"] = payload["samples"][-10000:]
        self._write(payload)
        return sample

    def list_samples(
        self,
        person_id: str | None = None,
    ) -> list[dict[str, Any]]:
        samples = list(self._read()["samples"])

        if person_id:
            samples = [
                sample
                for sample in samples
                if sample.get("person_id") == person_id
            ]

        return samples

    def add_event(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()
        event = {
            "id": uuid4().hex,
            "created_at": utc_now(),
            **item,
        }
        payload["recognition_events"].append(event)
        payload["recognition_events"] = payload["recognition_events"][-5000:]
        self._write(payload)
        return event

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self._read()["recognition_events"]))[:limit]

    def summary(self) -> dict[str, Any]:
        payload = self._read()
        known = sum(
            1
            for event in payload["recognition_events"]
            if event.get("recognized")
        )
        unknown = len(payload["recognition_events"]) - known

        return {
            "status": "ok",
            "person_count": len(payload["persons"]),
            "sample_count": len(payload["samples"]),
            "recognition_event_count": len(payload["recognition_events"]),
            "known_count": known,
            "unknown_count": unknown,
        }


face_identity_store = FaceIdentityStore()
