from __future__ import annotations

import base64
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from services.media_library.media_manager import media_library


ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "playback_nodes.json"
LEGACY_CONFIG = ROOT / "data" / "dual_audio_v15.json"


class PlaybackRoutingError(RuntimeError):
    pass


class NodeNotFoundError(PlaybackRoutingError):
    pass


class NodeUnavailableError(PlaybackRoutingError):
    pass


class NodeTrustError(PlaybackRoutingError):
    pass


class PlaybackRouter:
    """Routes home audio only to an explicitly selected room node."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._listen_sessions: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _default_document() -> dict[str, Any]:
        return {"version": 1, "nodes": []}

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(STORE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("nodes"), list):
                return data
        except (OSError, json.JSONDecodeError):
            pass
        if not STORE.exists():
            try:
                legacy = json.loads(LEGACY_CONFIG.read_text(encoding="utf-8"))
                url = str(legacy.get("pi_node_url") or "").strip().rstrip("/")
                if url.startswith(("http://", "https://")):
                    return {
                        "version": 1,
                        "nodes": [{
                            "node_id": "existing-pi-audio",
                            "name": str(legacy.get("pi_node_name") or "Existing Raspberry Pi"),
                            "room": str(legacy.get("room") or "Unassigned"),
                            "url": url,
                            "token": str(legacy.get("node_token") or ""),
                            "enabled": bool(legacy.get("pi_audio", True)),
                            "capabilities": {
                                "camera": False,
                                "microphone": str(legacy.get("input_mode") or "") in {"pi", "both"},
                                "speaker": bool(legacy.get("pi_audio", True)),
                                "playback": bool(legacy.get("pi_audio", True)),
                            },
                            "created_at": 0,
                            "updated_at": 0,
                        }],
                    }
            except (OSError, json.JSONDecodeError):
                pass
        return self._default_document()

    def _write(self, data: dict[str, Any]) -> None:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        temporary = STORE.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(STORE)

    @staticmethod
    def _normalize(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = {**(existing or {}), **payload}
        url = str(merged.get("url") or merged.get("base_url") or "").strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            raise ValueError("Node URL must begin with http:// or https://")
        name = str(merged.get("name") or "Room Pi").strip()
        room = str(merged.get("room") or "").strip()
        if not name or not room:
            raise ValueError("Node name and room are required")
        capabilities = merged.get("capabilities") or {}
        if not isinstance(capabilities, dict):
            capabilities = {}
        return {
            "node_id": str(merged.get("node_id") or uuid.uuid4().hex),
            "name": name[:100],
            "room": room[:100],
            "url": url,
            "token": str(merged.get("token") or "").strip(),
            "enabled": bool(merged.get("enabled", True)),
            "capabilities": {
                key: bool(capabilities.get(key, merged.get(key, False)))
                for key in ("camera", "microphone", "speaker", "playback")
            },
            "created_at": float(merged.get("created_at") or time.time()),
            "updated_at": time.time(),
        }

    @staticmethod
    def _public(node: dict[str, Any]) -> dict[str, Any]:
        return {**node, "token": "", "trusted": bool(node.get("token"))}

    def list_nodes(self, probe: bool = False) -> list[dict[str, Any]]:
        nodes = [self._public(item) for item in self._read()["nodes"]]
        if not probe:
            return nodes
        for node in nodes:
            try:
                health = self.health(node["node_id"])
                node.update({"online": True, "health": health, "last_seen": time.time()})
            except PlaybackRoutingError as error:
                node.update({"online": False, "health": {"status": "offline", "detail": str(error)}})
        return nodes

    def get_node(self, node_id: str) -> dict[str, Any]:
        node = next((row for row in self._read()["nodes"] if row.get("node_id") == node_id), None)
        if node is None:
            raise NodeNotFoundError("Target speaker node was not found")
        return node

    def create_node(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            node = self._normalize(payload)
            data["nodes"].append(node)
            self._write(data)
        return self._public(node)

    def update_node(self, node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            for index, current in enumerate(data["nodes"]):
                if current.get("node_id") != node_id:
                    continue
                updated = self._normalize(payload, current)
                updated["node_id"] = node_id
                data["nodes"][index] = updated
                self._write(data)
                return self._public(updated)
        raise NodeNotFoundError("Target speaker node was not found")

    def delete_node(self, node_id: str) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            original = len(data["nodes"])
            data["nodes"] = [row for row in data["nodes"] if row.get("node_id") != node_id]
            if len(data["nodes"]) == original:
                raise NodeNotFoundError("Target speaker node was not found")
            self._write(data)
        return {"status": "deleted", "node_id": node_id}

    @staticmethod
    def _request(node: dict[str, Any], path: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
        token = str(node.get("token") or "")
        if path != "/health" and not token:
            raise NodeTrustError("Target node requires a trust token")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["X-NoorBrain-Node-Token"] = token
        request = urllib.request.Request(node["url"] + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8")).get("detail")
            except Exception:
                detail = None
            raise NodeUnavailableError(detail or f"Target speaker returned HTTP {error.code}") from error
        except (OSError, urllib.error.URLError, TimeoutError) as error:
            raise NodeUnavailableError("Target speaker unavailable") from error
        if not isinstance(result, dict):
            raise NodeUnavailableError("Target speaker returned an invalid acknowledgement")
        return result

    def health(self, node_id: str) -> dict[str, Any]:
        return self._request(self.get_node(node_id), "/health", timeout=4)

    def _media_payload(self, media_id: str, volume: int | None) -> dict[str, Any]:
        item = media_library.get_item(media_id)
        path = media_library.get_file_path(media_id)
        return {
            "audio_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            "format": path.suffix.lstrip(".").lower() or "wav",
            "volume": volume,
            "media_id": media_id,
            "name": item.get("name") or item.get("original_filename"),
        }

    def play(self, payload: dict[str, Any]) -> dict[str, Any]:
        node_id = str(payload.get("target_node") or "").strip()
        if not node_id:
            raise ValueError("A target Raspberry Pi speaker is required")
        node = self.get_node(node_id)
        if not node.get("enabled") or not node.get("capabilities", {}).get("playback"):
            raise NodeUnavailableError("Target speaker playback is unavailable")
        kind = str(payload.get("type") or "tts").strip().lower()
        volume = payload.get("volume")
        if volume is not None:
            volume = max(0, min(int(volume), 100))

        if kind == "tts":
            text = str(payload.get("content") or "").strip()
            if not text:
                raise ValueError("Text message is required")
            acknowledgement = self._request(node, "/tts", method="POST", payload={"text": text, "volume": volume}, timeout=120)
        elif kind in {"media", "dua", "azkar", "reminder_audio"}:
            media_id = str(payload.get("media_id") or "").strip()
            if not media_id:
                raise ValueError("A Media Library item is required")
            acknowledgement = self._request(node, "/play", method="POST", payload=self._media_payload(media_id, volume), timeout=180)
        elif kind in {"audio", "intercom"}:
            audio = str(payload.get("audio_base64") or "")
            if not audio:
                raise ValueError("Recorded audio is required")
            base64.b64decode(audio, validate=True)
            acknowledgement = self._request(node, "/play", method="POST", payload={"audio_base64": audio, "format": str(payload.get("format") or "m4a"), "volume": volume}, timeout=180)
        else:
            raise ValueError("Unsupported playback type")

        if str(acknowledgement.get("status")) not in {"played", "accepted", "playing"}:
            raise NodeUnavailableError(str(acknowledgement.get("detail") or "Playback failed"))
        return {
            "status": "played",
            "target_node": node_id,
            "target_name": node.get("name"),
            "room": node.get("room"),
            "type": kind,
            "acknowledgement": acknowledgement,
            "laptop_playback": False,
        }

    def stop(self, node_id: str) -> dict[str, Any]:
        acknowledgement = self._request(self.get_node(node_id), "/stop", method="POST", payload={}, timeout=10)
        return {"status": str(acknowledgement.get("status") or "stopped"), "target_node": node_id, "acknowledgement": acknowledgement}

    def start_listen(self, node_id: str) -> dict[str, Any]:
        node = self.get_node(node_id)
        if not node.get("capabilities", {}).get("microphone"):
            raise NodeUnavailableError("Target room microphone is unavailable")
        acknowledgement = self._request(node, "/listen/start", method="POST", payload={}, timeout=10)
        node_session = str(acknowledgement.get("session_id") or "")
        if not node_session:
            raise NodeUnavailableError("Room node did not acknowledge listening")
        session_id = uuid.uuid4().hex
        with self._lock:
            self._listen_sessions[session_id] = {"node_id": node_id, "node_session": node_session, "created_at": time.time(), "last_seen": time.time()}
        return {"status": "listening", "session_id": session_id, "node_id": node_id, "room": node.get("room"), "remote_listening_active": True}

    def listen_chunk(self, session_id: str, seconds: int = 1) -> dict[str, Any]:
        with self._lock:
            session = self._listen_sessions.get(session_id)
            if session:
                session["last_seen"] = time.time()
        if not session:
            raise NodeNotFoundError("Listening session was not found")
        node = self.get_node(session["node_id"])
        return self._request(node, f"/listen/{session['node_session']}/chunk", method="POST", payload={"seconds": max(1, min(seconds, 3))}, timeout=10)

    def stop_listen(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self._listen_sessions.pop(session_id, None)
        if not session:
            return {"status": "stopped", "remote_listening_active": False}
        acknowledgement = self._request(self.get_node(session["node_id"]), f"/listen/{session['node_session']}/stop", method="POST", payload={}, timeout=10)
        return {"status": "stopped", "remote_listening_active": False, "acknowledgement": acknowledgement}


playback_router = PlaybackRouter()
