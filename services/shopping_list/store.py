from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


class ShoppingListStore:
    """Simple JSON-backed shopping list store for HALO voice management."""

    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "data" / "shopping_lists.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

    def _default_data(self) -> dict[str, Any]:
        return {
            "lists": {
                "shopping": [],
                "to_do": [],
                "reminders": [],
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            self.write(self._default_data())
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = self._default_data()
            self.write(data)
        data.setdefault("lists", {"shopping": [], "to_do": [], "reminders": []})
        return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def list_items(self, list_name: str = "shopping") -> list[dict[str, Any]]:
        data = self.read()
        return data.get("lists", {}).get(list_name, [])

    def add_item(
        self, text: str, list_name: str = "shopping"
    ) -> dict[str, Any]:
        data = self.read()
        if list_name not in data["lists"]:
            data["lists"][list_name] = []
        item = {
            "id": len(data["lists"][list_name]) + 1,
            "text": text,
            "checked": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data["lists"][list_name].append(item)
        self.write(data)
        return item

    def remove_item(
        self, item_id: int, list_name: str = "shopping"
    ) -> bool:
        data = self.read()
        items = data.get("lists", {}).get(list_name, [])
        for item in items:
            if item.get("id") == item_id:
                items.remove(item)
                data["lists"][list_name] = items
                self.write(data)
                return True
        return False

    def toggle_item(
        self, item_id: int, list_name: str = "shopping"
    ) -> dict[str, Any] | None:
        data = self.read()
        items = data.get("lists", {}).get(list_name, [])
        for item in items:
            if item.get("id") == item_id:
                item["checked"] = not item.get("checked", False)
                data["lists"][list_name] = items
                self.write(data)
                return item
        return None

    def clear_list(self, list_name: str = "shopping") -> int:
        data = self.read()
        items = data.get("lists", {}).get(list_name, [])
        count = len(items)
        data["lists"][list_name] = []
        self.write(data)
        return count

    def list_names(self) -> list[str]:
        data = self.read()
        return list(data.get("lists", {}).keys())


shopping_list_store = ShoppingListStore()
