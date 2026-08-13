from __future__ import annotations

import json
import socket
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, Body, HTTPException

router = APIRouter(
    prefix="/api/device-ecosystem-v7",
    tags=["Device Ecosystem v7"],
)

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "device_ecosystem_v7.json"
SMART_HOME_STORE = ROOT / "data" / "smart_home_v3.json"

DEFAULT: dict[str, Any] = {
    "version": 1,
    "candidates": [],
    "paired": [],
    "settings": {
        "auto_discovery": True,
        "health_interval_seconds": 30,
        "default_room": "hall",
    },
}


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        write_json(path, default)
        return json.loads(json.dumps(default))

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    result = json.loads(json.dumps(default))

    if isinstance(data, dict):
        result.update(data)

    return result


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(path)


def store() -> dict[str, Any]:
    data = read_json(STORE, DEFAULT)
    data.setdefault("candidates", [])
    data.setdefault("paired", [])
    data.setdefault("settings", DEFAULT["settings"].copy())
    return data


def save(data: dict[str, Any]) -> None:
    write_json(STORE, data)


def normalize_url(value: str) -> str:
    value = value.strip()

    if not value:
        return ""

    if "://" not in value:
        value = "http://" + value

    parsed = urlparse(value)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=422,
            detail="Device URL must be HTTP or HTTPS.",
        )

    return value.rstrip("/")


def probe(url: str, timeout: float = 2.0) -> dict[str, Any]:
    started = time.monotonic()

    try:
        request = Request(
            url,
            headers={"User-Agent": "NoorBrain/7.0"},
            method="GET",
        )

        with urlopen(request, timeout=timeout) as response:
            elapsed = int((time.monotonic() - started) * 1000)

            return {
                "online": response.status < 500,
                "http_status": response.status,
                "latency_ms": elapsed,
                "error": "",
            }
    except Exception as exc:
        elapsed = int((time.monotonic() - started) * 1000)

        return {
            "online": False,
            "http_status": 0,
            "latency_ms": elapsed,
            "error": str(exc),
        }


def arp_candidates() -> list[dict[str, Any]]:
    path = Path("/proc/net/arp")

    if not path.exists():
        return []

    rows = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()[1:]

    found = []

    for row in rows:
        parts = row.split()

        if len(parts) < 6:
            continue

        ip, _, flags, mac, _, interface = parts[:6]

        if flags == "0x0" or mac == "00:00:00:00:00:00":
            continue

        found.append(
            {
                "id": f"arp-{ip.replace('.', '-')}",
                "name": f"Network Device {ip}",
                "host": ip,
                "base_url": f"http://{ip}",
                "mac": mac,
                "interface": interface,
                "source": "arp",
                "type": "unknown",
                "discovered_at": int(time.time()),
            }
        )

    return found


def local_host_candidates() -> list[dict[str, Any]]:
    candidates = []

    try:
        hostname = socket.gethostname()
        addresses = socket.gethostbyname_ex(hostname)[2]
    except Exception:
        addresses = []

    for ip in addresses:
        if ip.startswith("127."):
            continue

        candidates.append(
            {
                "id": f"local-{ip.replace('.', '-')}",
                "name": f"NoorBrain Host {ip}",
                "host": ip,
                "base_url": f"http://{ip}:8001",
                "mac": "",
                "interface": "local",
                "source": "local",
                "type": "noorbrain",
                "discovered_at": int(time.time()),
            }
        )

    return candidates


def merge_candidates(
    current: list[dict[str, Any]],
    discovered: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}

    for item in current + discovered:
        key = (
            str(item.get("mac") or "").lower()
            or str(item.get("base_url") or "").lower()
            or str(item.get("host") or "").lower()
            or str(item.get("id") or "")
        )

        if not key:
            continue

        existing = by_key.get(key, {})
        existing.update(item)
        by_key[key] = existing

    return list(by_key.values())


def smart_home_data() -> dict[str, Any]:
    default = {
        "version": 1,
        "rooms": [
            {"id": "hall", "name": "Hall", "icon": "🛋️"},
        ],
        "devices": [],
        "scenes": [],
        "favorites": [],
    }

    data = read_json(SMART_HOME_STORE, default)
    data.setdefault("rooms", default["rooms"])
    data.setdefault("devices", [])
    data.setdefault("scenes", [])
    data.setdefault("favorites", [])
    return data


def bridge_device(device: dict[str, Any]) -> str:
    data = smart_home_data()

    existing = next(
        (
            item
            for item in data["devices"]
            if item.get("ecosystem_id") == device["id"]
        ),
        None,
    )

    smart_id = existing.get("id") if existing else uuid.uuid4().hex[:12]

    smart_device = {
        "id": smart_id,
        "ecosystem_id": device["id"],
        "name": device["name"],
        "type": device["type"],
        "room_id": device["room_id"],
        "state": device.get("state", "off"),
        "online": device.get("online", False),
        "webhook_on": device.get("command_on", ""),
        "webhook_off": device.get("command_off", ""),
        "health_url": device.get("health_url", ""),
    }

    if existing:
        existing.update(smart_device)
    else:
        data["devices"].append(smart_device)

    write_json(SMART_HOME_STORE, data)
    return smart_id


@router.get("/health")
def health() -> dict[str, Any]:
    data = store()

    return {
        "status": "healthy",
        "service": "device_ecosystem_v7",
        "version": "7.0.0",
        "candidates": len(data["candidates"]),
        "paired": len(data["paired"]),
    }


@router.get("/state")
def state() -> dict[str, Any]:
    return {
        "status": "ok",
        "ecosystem": store(),
    }


@router.post("/discover")
def discover() -> dict[str, Any]:
    data = store()
    discovered = local_host_candidates() + arp_candidates()

    paired_keys = {
        str(item.get("base_url") or "").lower()
        for item in data["paired"]
    }

    discovered = [
        item
        for item in discovered
        if str(item.get("base_url") or "").lower() not in paired_keys
    ]

    data["candidates"] = merge_candidates(
        data["candidates"],
        discovered,
    )

    save(data)

    return {
        "status": "completed",
        "found": len(discovered),
        "candidates": data["candidates"],
    }


@router.post("/candidates")
def add_candidate(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    base_url = normalize_url(
        str(payload.get("base_url") or payload.get("host") or "")
    )

    name = str(payload.get("name") or "").strip()

    if not name:
        name = urlparse(base_url).hostname or "New Device"

    data = store()

    candidate = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "host": urlparse(base_url).hostname or "",
        "base_url": base_url,
        "mac": str(payload.get("mac") or ""),
        "interface": "manual",
        "source": "manual",
        "type": str(payload.get("type") or "switch"),
        "discovered_at": int(time.time()),
    }

    data["candidates"] = merge_candidates(
        data["candidates"],
        [candidate],
    )

    save(data)

    return {
        "status": "created",
        "candidate": candidate,
    }


@router.post("/candidates/{candidate_id}/probe")
def probe_candidate(
    candidate_id: str,
) -> dict[str, Any]:
    data = store()

    candidate = next(
        (
            item
            for item in data["candidates"]
            if item.get("id") == candidate_id
        ),
        None,
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found.",
        )

    result = probe(candidate["base_url"])
    candidate["probe"] = result
    candidate["last_seen"] = int(time.time()) if result["online"] else 0
    save(data)

    return {
        "status": "ok",
        "candidate": candidate,
    }


@router.post("/pair")
def pair(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    candidate_id = str(payload.get("candidate_id") or "")
    data = store()

    candidate = next(
        (
            item
            for item in data["candidates"]
            if item.get("id") == candidate_id
        ),
        None,
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found.",
        )

    device_type = str(
        payload.get("type")
        or candidate.get("type")
        or "switch"
    ).strip()

    base_url = normalize_url(
        str(payload.get("base_url") or candidate.get("base_url") or "")
    )

    health_path = str(
        payload.get("health_path") or "/"
    ).strip()

    command_on_path = str(
        payload.get("command_on_path") or ""
    ).strip()

    command_off_path = str(
        payload.get("command_off_path") or ""
    ).strip()

    def endpoint(path: str) -> str:
        if not path:
            return ""

        if path.startswith("http://") or path.startswith("https://"):
            return path

        return base_url + "/" + path.lstrip("/")

    device = {
        "id": uuid.uuid4().hex[:12],
        "name": str(
            payload.get("name")
            or candidate.get("name")
            or "Smart Device"
        ).strip(),
        "type": device_type,
        "room_id": str(
            payload.get("room_id")
            or data["settings"].get("default_room")
            or "hall"
        ),
        "base_url": base_url,
        "health_url": endpoint(health_path),
        "command_on": endpoint(command_on_path),
        "command_off": endpoint(command_off_path),
        "state": "off",
        "online": False,
        "paired_at": int(time.time()),
        "source_candidate": candidate_id,
    }

    result = probe(device["health_url"])
    device["online"] = result["online"]
    device["last_health"] = result

    smart_home_id = bridge_device(device)
    device["smart_home_id"] = smart_home_id

    data["paired"].append(device)
    data["candidates"] = [
        item
        for item in data["candidates"]
        if item.get("id") != candidate_id
    ]

    save(data)

    return {
        "status": "paired",
        "device": device,
    }


@router.post("/paired/{device_id}/health")
def check_device_health(
    device_id: str,
) -> dict[str, Any]:
    data = store()

    device = next(
        (
            item
            for item in data["paired"]
            if item.get("id") == device_id
        ),
        None,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Paired device not found.",
        )

    result = probe(device.get("health_url") or device["base_url"])
    device["online"] = result["online"]
    device["last_health"] = result
    device["last_seen"] = int(time.time()) if result["online"] else 0

    bridge_device(device)
    save(data)

    return {
        "status": "ok",
        "device": device,
    }


@router.post("/paired/health-all")
def check_all_health() -> dict[str, Any]:
    data = store()
    results = []

    for device in data["paired"]:
        result = probe(
            device.get("health_url")
            or device.get("base_url")
            or ""
        )

        device["online"] = result["online"]
        device["last_health"] = result
        device["last_seen"] = int(time.time()) if result["online"] else 0

        bridge_device(device)

        results.append(
            {
                "id": device["id"],
                "online": device["online"],
                "latency_ms": result["latency_ms"],
            }
        )

    save(data)

    return {
        "status": "completed",
        "results": results,
    }


@router.delete("/paired/{device_id}")
def unpair(
    device_id: str,
) -> dict[str, Any]:
    data = store()

    device = next(
        (
            item
            for item in data["paired"]
            if item.get("id") == device_id
        ),
        None,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Paired device not found.",
        )

    data["paired"] = [
        item
        for item in data["paired"]
        if item.get("id") != device_id
    ]

    smart = smart_home_data()
    smart["devices"] = [
        item
        for item in smart["devices"]
        if item.get("ecosystem_id") != device_id
    ]

    write_json(SMART_HOME_STORE, smart)
    save(data)

    return {
        "status": "unpaired",
        "device_id": device_id,
    }


@router.post("/settings")
def update_settings(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    data = store()

    for key in (
        "auto_discovery",
        "health_interval_seconds",
        "default_room",
    ):
        if key in payload:
            data["settings"][key] = payload[key]

    save(data)

    return {
        "status": "updated",
        "settings": data["settings"],
    }
