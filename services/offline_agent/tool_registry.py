from __future__ import annotations
from typing import Any, Callable

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self._dangerous: set[str] = set()

    def register(self, name: str, handler: Callable[[dict[str, Any]], dict[str, Any]], *, requires_confirmation: bool = False) -> None:
        self._tools[name] = handler
        if requires_confirmation:
            self._dangerous.add(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def requires_confirmation(self, name: str) -> bool:
        return name in self._dangerous

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = self._tools.get(name)
        if handler is None:
            raise KeyError(f"Unknown tool: {name}")
        return handler(arguments)

tool_registry = ToolRegistry()
