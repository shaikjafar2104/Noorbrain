from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np


class UnknownFaceGallery:
    """Privacy-local review gallery for unknown faces.

    Unknown detections are snapshots only. They are never silently promoted to
    a named/family identity. Similar consecutive frames are deduplicated.
    """

    def __init__(self) -> None:
        self.root = Path("data/person_profiles/unknown_gallery")
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.lock = threading.RLock()
        self.minimum_interval = 20.0
        self.maximum_items = 200
        self.last_saved = 0.0

    def _read(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            items = payload.get("items", [])
            return items if isinstance(items, list) else []
        except Exception:
            return []

    def _write(self, items: list[dict[str, Any]]) -> None:
        temporary = self.index_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"version": 1, "items": items}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.index_path)

    @staticmethod
    def _fingerprint(image: np.ndarray) -> str:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
        bits = small >= float(small.mean())
        packed = np.packbits(bits.reshape(-1).astype(np.uint8))
        return packed.tobytes().hex()

    @staticmethod
    def _distance(first: str, second: str) -> int:
        try:
            return sum((a ^ b).bit_count() for a, b in zip(bytes.fromhex(first), bytes.fromhex(second)))
        except Exception:
            return 999

    def capture(self, frame: np.ndarray, results: list[dict[str, Any]]) -> dict[str, Any]:
        now = time.time()
        if now - self.last_saved < self.minimum_interval:
            return {"status": "cooldown", "saved": 0}

        height, width = frame.shape[:2]
        saved = 0
        with self.lock:
            items = self._read()
            for result in results:
                if result.get("status") != "unknown":
                    continue
                box = result.get("box")
                if not isinstance(box, (list, tuple)) or len(box) != 4:
                    continue
                x, y, w, h = [int(value) for value in box]
                padding = max(10, int(max(w, h) * 0.18))
                x1, y1 = max(0, x - padding), max(0, y - padding)
                x2, y2 = min(width, x + w + padding), min(height, y + h + padding)
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0 or crop.shape[0] < 40 or crop.shape[1] < 40:
                    continue
                fingerprint = self._fingerprint(crop)
                if any(
                    self._distance(fingerprint, str(item.get("fingerprint", ""))) <= 18
                    and now - float(item.get("timestamp", 0)) < 1800
                    for item in items[-40:]
                ):
                    continue
                item_id = uuid.uuid4().hex
                filename = f"{item_id}.jpg"
                if not cv2.imwrite(str(self.root / filename), crop, [cv2.IMWRITE_JPEG_QUALITY, 88]):
                    continue
                items.append({
                    "id": item_id,
                    "filename": filename,
                    "timestamp": now,
                    "confidence": result.get("confidence"),
                    "fingerprint": fingerprint,
                    "status": "needs_review",
                })
                saved += 1
                self.last_saved = now
                break

            while len(items) > self.maximum_items:
                removed = items.pop(0)
                (self.root / str(removed.get("filename", ""))).unlink(missing_ok=True)
            self._write(items)

        return {"status": "saved" if saved else "duplicate", "saved": saved}

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.lock:
            items = list(reversed(self._read()))[:max(1, min(int(limit), 200))]
        return [{**item, "image_url": f"/api/person-gallery/unknown/{item['id']}/image"} for item in items]

    def image_path(self, item_id: str) -> Path | None:
        with self.lock:
            item = next((row for row in self._read() if row.get("id") == item_id), None)
        if not item:
            return None
        path = self.root / str(item.get("filename", ""))
        return path if path.is_file() else None

    def delete(self, item_id: str) -> bool:
        with self.lock:
            items = self._read()
            item = next((row for row in items if row.get("id") == item_id), None)
            if not item:
                return False
            retained = [row for row in items if row.get("id") != item_id]
            (self.root / str(item.get("filename", ""))).unlink(missing_ok=True)
            self._write(retained)
        return True


unknown_face_gallery = UnknownFaceGallery()
