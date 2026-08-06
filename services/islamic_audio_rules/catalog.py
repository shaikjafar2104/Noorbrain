from __future__ import annotations

import hashlib
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MEDIA_ROOT = ROOT / "media" / "audio"
DATABASE = ROOT / "data" / "media_library.json"
DUAS = MEDIA_ROOT / "islamic" / "duas"
AZKAR = MEDIA_ROOT / "islamic" / "azkar"


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _dua_titles() -> dict[str, str]:
    rows = _load_json(DUAS / "manifest.json", [])
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("file")): str(row.get("title") or Path(str(row.get("file"))).stem)
        for row in rows
        if isinstance(row, dict) and row.get("file")
    }


def _stable_id(relative_path: str) -> str:
    digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:24]
    return f"islamic-{digest}"


def sync_catalog() -> dict[str, Any]:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    document = _load_json(DATABASE, {"version": 1, "items": []})
    if not isinstance(document, dict):
        document = {"version": 1, "items": []}
    items = document.get("items")
    if not isinstance(items, list):
        items = []

    dua_titles = _dua_titles()
    discovered: list[tuple[Path, str, str]] = []
    if DUAS.is_dir():
        for path in sorted(DUAS.glob("*.mp3")):
            discovered.append((path, "duas", dua_titles.get(path.name, path.stem)))
    if AZKAR.is_dir():
        for path in sorted(AZKAR.glob("*.mp3")):
            discovered.append((path, "azkar", "Azkar – 99 Names of Allah"))

    by_path = {
        str(item.get("relative_path")): item
        for item in items
        if isinstance(item, dict) and item.get("relative_path")
    }
    added = 0
    for path, category, title in discovered:
        relative = path.relative_to(MEDIA_ROOT).as_posix()
        if relative in by_path:
            item = by_path[relative]
            item["category"] = category
            item["name"] = title
            continue
        media_id = _stable_id(relative)
        item = {
            "id": media_id,
            "name": title,
            "original_filename": path.name,
            "stored_filename": path.name,
            "category": category,
            "relative_path": relative,
            "extension": ".mp3",
            "mime_type": mimetypes.guess_type(path.name)[0] or "audio/mpeg",
            "size_bytes": path.stat().st_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_url": f"/media/{media_id}/file",
            "api_file_url": f"/api/media/{media_id}/file",
            "managed_by": "islamic_audio_rules",
        }
        items.append(item)
        by_path[relative] = item
        added += 1

    document["version"] = max(1, int(document.get("version", 1)))
    document["items"] = items
    temporary = DATABASE.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(DATABASE)
    return {"found": len(discovered), "added": added}


def catalog_items() -> list[dict[str, Any]]:
    sync_catalog()
    document = _load_json(DATABASE, {"items": []})
    items = document.get("items", []) if isinstance(document, dict) else []
    selected = [
        item for item in items
        if isinstance(item, dict) and item.get("category") in {"duas", "azkar"}
    ]
    return sorted(selected, key=lambda item: (item.get("category") != "duas", item.get("name", "")))
