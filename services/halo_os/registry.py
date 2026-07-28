from __future__ import annotations

from threading import RLock
from typing import Any

from .builtin_skills import load_builtin_skills
from .contracts import LoadedSkill


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, LoadedSkill] = {}
        self._lock = RLock()
        self.reload()

    def reload(self) -> dict[str, Any]:
        loaded = load_builtin_skills()

        with self._lock:
            self._skills = {
                skill.manifest.name: skill
                for skill in loaded
            }

        return self.summary()

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._skills)

    def get(self, name: str) -> LoadedSkill | None:
        with self._lock:
            return self._skills.get(name)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            skills = list(self._skills.values())

        return [skill.public_dict() for skill in skills]

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        skill = self.get(name)
        if skill is None:
            raise KeyError(f"HALO skill not found: {name}")

        return skill.execute(arguments)

    def health(self) -> dict[str, Any]:
        skills = self.list()
        unavailable = [
            item["name"]
            for item in skills
            if item["health"].get("status") == "unavailable"
        ]
        degraded = [
            item["name"]
            for item in skills
            if item["health"].get("status") == "degraded"
        ]

        return {
            "status": "healthy" if not unavailable else "degraded",
            "skill_count": len(skills),
            "unavailable": unavailable,
            "degraded": degraded,
            "skills": skills,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "count": len(self.names()),
            "skills": self.names(),
        }


skill_registry = SkillRegistry()
