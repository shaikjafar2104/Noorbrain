from __future__ import annotations

import json
import mimetypes
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEDIA_ROOT = PROJECT_ROOT / "media" / "audio"
DATABASE_PATH = PROJECT_ROOT / "data" / "media_library.json"

DEFAULT_CATEGORIES = (
    "islamic",
    "personal",
    "alerts",
    "custom",
)

ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
    ".flac",
    ".aac",
}

MAX_FILE_SIZE = 50 * 1024 * 1024


class MediaLibraryError(Exception):
    """Base media-library error."""


class InvalidMediaError(MediaLibraryError):
    """Raised when an uploaded media file is invalid."""


class MediaNotFoundError(MediaLibraryError):
    """Raised when a requested media item does not exist."""


class MediaLibraryManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._playback_lock = threading.RLock()
        self._active_process: subprocess.Popen[Any] | None = None

        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

        for category in DEFAULT_CATEGORIES:
            (MEDIA_ROOT / category).mkdir(parents=True, exist_ok=True)

        if not DATABASE_PATH.exists():
            self._write_database({"version": 1, "items": []})

        self._reconcile_files()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_category(value: str | None) -> str:
        category = (value or "custom").strip().lower()
        category = re.sub(r"[^a-z0-9_-]+", "-", category).strip("-_")

        if not category:
            category = "custom"

        return category[:50]

    @staticmethod
    def _safe_filename(filename: str) -> str:
        original = Path(filename or "audio").name
        stem = Path(original).stem
        extension = Path(original).suffix.lower()

        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-_")
        if not stem:
            stem = "audio"

        return f"{stem[:100]}{extension}"

    def _read_database(self) -> dict[str, Any]:
        with self._lock:
            try:
                with DATABASE_PATH.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError):
                data = {"version": 1, "items": []}

            if not isinstance(data, dict):
                data = {"version": 1, "items": []}

            if not isinstance(data.get("items"), list):
                data["items"] = []

            return data

    def _write_database(self, data: dict[str, Any]) -> None:
        with self._lock:
            temporary = DATABASE_PATH.with_suffix(".tmp")

            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)

            temporary.replace(DATABASE_PATH)

    def _reconcile_files(self) -> None:
        data = self._read_database()
        changed = False
        valid_items: list[dict[str, Any]] = []

        for item in data["items"]:
            relative_path = item.get("relative_path")

            if not relative_path:
                changed = True
                continue

            full_path = MEDIA_ROOT / relative_path

            if not full_path.exists() or not full_path.is_file():
                changed = True
                continue

            valid_items.append(item)

        if changed:
            data["items"] = valid_items
            self._write_database(data)

    def list_categories(self) -> list[dict[str, Any]]:
        data = self._read_database()
        counts: dict[str, int] = {}

        for item in data["items"]:
            category = str(item.get("category") or "custom")
            counts[category] = counts.get(category, 0) + 1

        directory_names = {
            path.name
            for path in MEDIA_ROOT.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        }

        all_categories = sorted(
            set(DEFAULT_CATEGORIES) | directory_names | set(counts)
        )

        return [
            {
                "name": category,
                "count": counts.get(category, 0),
            }
            for category in all_categories
        ]

    def create_category(self, name: str) -> dict[str, Any]:
        category = self._safe_category(name)
        category_path = MEDIA_ROOT / category
        category_path.mkdir(parents=True, exist_ok=True)

        return {
            "name": category,
            "count": sum(
                1
                for item in self.list_items()
                if item["category"] == category
            ),
        }

    def list_items(
        self,
        category: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        data = self._read_database()
        items = list(data["items"])

        if category:
            normalized_category = self._safe_category(category)
            items = [
                item
                for item in items
                if item.get("category") == normalized_category
            ]

        if search:
            needle = search.strip().lower()
            items = [
                item
                for item in items
                if needle in str(item.get("name", "")).lower()
                or needle in str(item.get("original_filename", "")).lower()
                or needle in str(item.get("category", "")).lower()
            ]

        return sorted(
            items,
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

    def get_item(self, media_id: str) -> dict[str, Any]:
        for item in self.list_items():
            if item.get("id") == media_id:
                return item

        raise MediaNotFoundError("Audio file was not found.")

    def get_file_path(self, media_id: str) -> Path:
        item = self.get_item(media_id)
        relative_path = str(item["relative_path"])
        file_path = (MEDIA_ROOT / relative_path).resolve()

        media_root_resolved = MEDIA_ROOT.resolve()

        if (
            media_root_resolved not in file_path.parents
            or not file_path.exists()
            or not file_path.is_file()
        ):
            raise MediaNotFoundError("Audio file was not found.")

        return file_path

    def save_upload(
        self,
        file_stream: BinaryIO,
        original_filename: str,
        category: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        extension = Path(original_filename or "").suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            supported = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise InvalidMediaError(
                f"Unsupported file type. Supported formats: {supported}"
            )

        normalized_category = self._safe_category(category)
        category_path = MEDIA_ROOT / normalized_category
        category_path.mkdir(parents=True, exist_ok=True)

        safe_filename = self._safe_filename(original_filename)
        unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"
        destination = category_path / unique_filename

        total_size = 0

        try:
            with destination.open("wb") as output:
                while True:
                    chunk = file_stream.read(1024 * 1024)

                    if not chunk:
                        break

                    total_size += len(chunk)

                    if total_size > MAX_FILE_SIZE:
                        raise InvalidMediaError(
                            "Audio file is larger than the 50 MB limit."
                        )

                    output.write(chunk)

        except Exception:
            destination.unlink(missing_ok=True)
            raise

        if total_size == 0:
            destination.unlink(missing_ok=True)
            raise InvalidMediaError("Uploaded audio file is empty.")

        media_id = uuid.uuid4().hex
        mime_type = (
            mimetypes.guess_type(destination.name)[0]
            or "application/octet-stream"
        )

        clean_display_name = (
            display_name.strip()
            if display_name and display_name.strip()
            else Path(safe_filename).stem
        )

        item = {
            "id": media_id,
            "name": clean_display_name[:150],
            "original_filename": Path(original_filename).name,
            "stored_filename": unique_filename,
            "category": normalized_category,
            "relative_path": str(
                Path(normalized_category) / unique_filename
            ),
            "extension": extension,
            "mime_type": mime_type,
            "size_bytes": total_size,
            "created_at": self._now(),
            "file_url": f"/media/{media_id}/file",
            "api_file_url": f"/api/media/{media_id}/file",
        }

        data = self._read_database()
        data["items"].append(item)
        self._write_database(data)

        return item

    def delete_item(self, media_id: str) -> dict[str, Any]:
        data = self._read_database()
        matching_item: dict[str, Any] | None = None
        retained_items: list[dict[str, Any]] = []

        for item in data["items"]:
            if item.get("id") == media_id:
                matching_item = item
            else:
                retained_items.append(item)

        if matching_item is None:
            raise MediaNotFoundError("Audio file was not found.")

        file_path = MEDIA_ROOT / str(matching_item["relative_path"])
        file_path.unlink(missing_ok=True)

        data["items"] = retained_items
        self._write_database(data)

        return matching_item

    @staticmethod
    def _find_player(file_path: Path) -> list[str] | None:
        extension = file_path.suffix.lower()

        players: list[list[str]] = [
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(file_path)],
            ["cvlc", "--play-and-exit", "--intf", "dummy", str(file_path)],
            ["mpv", "--no-video", "--really-quiet", str(file_path)],
            ["paplay", str(file_path)],
        ]

        if extension == ".wav":
            players.append(["aplay", "-q", str(file_path)])

        if extension == ".mp3":
            players.append(["mpg123", "-q", str(file_path)])

        for command in players:
            if shutil.which(command[0]):
                return command

        return None

    def play_item(self, media_id: str) -> dict[str, Any]:
        item = self.get_item(media_id)
        file_path = self.get_file_path(media_id)
        command = self._find_player(file_path)

        if command is None:
            raise MediaLibraryError(
                "No supported audio player was found. "
                "Install ffmpeg, VLC, mpv, mpg123, or PulseAudio utilities."
            )

        with self._playback_lock:
            if (
                self._active_process is not None
                and self._active_process.poll() is None
            ):
                self._active_process.terminate()

                try:
                    self._active_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._active_process.kill()

            self._active_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        return {
            "status": "playing",
            "player": command[0],
            "item": item,
        }

    def stop_playback(self) -> dict[str, Any]:
        with self._playback_lock:
            if (
                self._active_process is None
                or self._active_process.poll() is not None
            ):
                self._active_process = None
                return {"status": "idle"}

            self._active_process.terminate()

            try:
                self._active_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._active_process.kill()

            self._active_process = None

        return {"status": "stopped"}

    def status(self) -> dict[str, Any]:
        items = self.list_items()

        with self._playback_lock:
            playing = (
                self._active_process is not None
                and self._active_process.poll() is None
            )

        return {
            "status": "running",
            "total_items": len(items),
            "total_size_bytes": sum(
                int(item.get("size_bytes", 0))
                for item in items
            ),
            "categories": self.list_categories(),
            "supported_extensions": sorted(ALLOWED_EXTENSIONS),
            "max_file_size_bytes": MAX_FILE_SIZE,
            "playing": playing,
        }


media_library = MediaLibraryManager()
