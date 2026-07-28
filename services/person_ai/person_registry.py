import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class PersonRegistry:
    def __init__(self):
        self.file = Path("data/person_profiles/persons.json")
        self.lock = threading.RLock()
        self.data: dict[str, Any] = {}
        self._load()

    def _default_data(self):
        return {
            "version": "5.1",
            "persons": [],
        }

    def _load(self):
        with self.lock:
            self.file.parent.mkdir(parents=True, exist_ok=True)

            if not self.file.exists():
                self.data = self._default_data()
                self._save()
                return

            try:
                with self.file.open("r", encoding="utf-8") as file:
                    loaded = json.load(file)

                if not isinstance(loaded, dict):
                    raise ValueError("Registry root must be an object")

                if not isinstance(loaded.get("persons"), list):
                    raise ValueError("persons must be a list")

                self.data = loaded

            except (json.JSONDecodeError, OSError, ValueError):
                corrupt_file = self.file.with_suffix(
                    f".corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )

                try:
                    self.file.replace(corrupt_file)
                except OSError:
                    pass

                self.data = self._default_data()
                self._save()

    def _save(self):
        with self.lock:
            self.file.parent.mkdir(parents=True, exist_ok=True)

            temporary_file = self.file.with_suffix(".tmp")

            with temporary_file.open("w", encoding="utf-8") as file:
                json.dump(
                    self.data,
                    file,
                    indent=4,
                    ensure_ascii=False,
                )

            temporary_file.replace(self.file)

    def all(self):
        with self.lock:
            return [dict(person) for person in self.data["persons"]]

    def get(self, person_id: str):
        with self.lock:
            for person in self.data["persons"]:
                if person.get("person_id") == person_id:
                    return dict(person)

        return None

    def create(
        self,
        name: str,
        category: str,
        relationship: str | None = None,
        preferred_language: str = "English",
        notes: str | None = None,
        active: bool = True,
    ):
        now = datetime.now().astimezone().isoformat()

        person = {
            "person_id": str(uuid.uuid4()),
            "name": name.strip(),
            "category": category.strip().lower(),
            "relationship": relationship.strip() if relationship else None,
            "preferred_language": preferred_language.strip(),
            "notes": notes.strip() if notes else None,
            "active": active,
            "face_registered": False,
            "face_samples": 0,
            "created_at": now,
            "updated_at": now,
        }

        with self.lock:
            self.data["persons"].append(person)
            self._save()

        return dict(person)

    def update_face_info(
        self,
        person_id: str,
        samples: int,
    ):
        now = datetime.now().astimezone().isoformat()

        with self.lock:
            for person in self.data["persons"]:
                if person.get("person_id") == person_id:
                    person["face_registered"] = samples > 0
                    person["face_samples"] = int(samples)
                    person["updated_at"] = now
                    self._save()
                    return dict(person)

        return None


registry = PersonRegistry()
