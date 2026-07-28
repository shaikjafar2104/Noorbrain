from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


HealthHandler = Callable[[], dict[str, Any]]
ExecuteHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class SkillManifest:
    name: str
    title: str
    version: str
    description: str
    intents: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    requires_confirmation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedSkill:
    manifest: SkillManifest
    execute: ExecuteHandler
    health: HealthHandler

    def public_dict(self) -> dict[str, Any]:
        health = self.health()
        return {
            "name": self.manifest.name,
            "title": self.manifest.title,
            "version": self.manifest.version,
            "description": self.manifest.description,
            "intents": list(self.manifest.intents),
            "permissions": list(self.manifest.permissions),
            "requires_confirmation": self.manifest.requires_confirmation,
            "metadata": dict(self.manifest.metadata),
            "health": health,
        }
