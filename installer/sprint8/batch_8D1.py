#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


SERVICE_INIT = '''from .routes import router

__all__ = ["router"]
'''


STORE_PY = r'''from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ConversationMemoryStore:
    def __init__(self) -> None:
        self.path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "halo_conversation_memory_v8.json"
        )
        self.lock = threading.RLock()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "8.4.0",
            "sessions": {},
            "updated_at": self.now(),
        }

    def read(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.is_file():
                return self.default()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return self.default()
            if not isinstance(data.get("sessions"), dict):
                data["sessions"] = {}
            return data

    def write(self, data: dict[str, Any]) -> None:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = self.now()
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)

    def remember(
        self,
        session_id: str,
        role: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            session = data["sessions"].setdefault(
                session_id,
                {
                    "id": session_id,
                    "created_at": self.now(),
                    "messages": [],
                    "facts": {},
                },
            )
            message = {
                "id": uuid4().hex,
                "role": role,
                "text": text,
                "metadata": metadata or {},
                "created_at": self.now(),
            }
            session["messages"].append(message)
            session["messages"] = session["messages"][-200:]
            session["updated_at"] = self.now()
            self.write(data)
            return message

    def set_fact(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            session = data["sessions"].setdefault(
                session_id,
                {
                    "id": session_id,
                    "created_at": self.now(),
                    "messages": [],
                    "facts": {},
                },
            )
            session.setdefault("facts", {})[key] = value
            session["updated_at"] = self.now()
            self.write(data)
            return session["facts"]

    def context(self, session_id: str, limit: int = 20) -> dict[str, Any]:
        data = self.read()
        session = data["sessions"].get(session_id)
        if session is None:
            return {
                "id": session_id,
                "messages": [],
                "facts": {},
            }
        result = dict(session)
        result["messages"] = list(session.get("messages", []))[-limit:]
        return result

    def clear(self, session_id: str) -> bool:
        with self.lock:
            data = self.read()
            removed = data["sessions"].pop(session_id, None) is not None
            if removed:
                self.write(data)
            return removed


conversation_memory_store = ConversationMemoryStore()
'''


ROUTES_PY = r'''from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .store import conversation_memory_store


router = APIRouter(
    prefix="/api/halo-memory-v8",
    tags=["HALO Conversation Memory V8"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    data = await asyncio.to_thread(conversation_memory_store.read)
    return {
        "status": "healthy",
        "service": "halo_conversation_memory_v8",
        "version": "8.4.0",
        "sessions": len(data.get("sessions", {})),
    }


@router.post("/sessions/{session_id}/remember")
async def remember(
    session_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    role = str(payload.get("role") or "user").strip().lower()
    text = str(payload.get("text") or "").strip()
    if role not in {"user", "assistant", "system"}:
        raise HTTPException(status_code=422, detail="Invalid role.")
    if not text:
        raise HTTPException(status_code=422, detail="Text is required.")
    message = await asyncio.to_thread(
        conversation_memory_store.remember,
        session_id,
        role,
        text,
        payload.get("metadata") or {},
    )
    return {"status": "remembered", "message": message}


@router.put("/sessions/{session_id}/facts/{key}")
async def set_fact(
    session_id: str,
    key: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    if "value" not in payload:
        raise HTTPException(status_code=422, detail="Value is required.")
    facts = await asyncio.to_thread(
        conversation_memory_store.set_fact,
        session_id,
        key,
        payload["value"],
    )
    return {"status": "updated", "facts": facts}


@router.get("/sessions/{session_id}/context")
async def context(
    session_id: str,
    limit: int = Query(20, ge=1, le=200),
) -> dict[str, Any]:
    session = await asyncio.to_thread(
        conversation_memory_store.context,
        session_id,
        limit,
    )
    return {"status": "ok", "session": session}


@router.delete("/sessions/{session_id}")
async def clear(session_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        conversation_memory_store.clear,
        session_id,
    )
    return {"status": "cleared", "removed": removed}
'''


SMOKE_TEST = r'''from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001/api/halo-memory-v8"
SESSION = "sprint8d1-smoke"


def call(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        BASE + path,
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


health = call("/health")
assert health["version"] == "8.4.0"

call(f"/sessions/{SESSION}", "DELETE")

remembered = call(
    f"/sessions/{SESSION}/remember",
    "POST",
    {"role": "user", "text": "My preferred room is Hall."},
)
assert remembered["status"] == "remembered"

facts = call(
    f"/sessions/{SESSION}/facts/preferred_room",
    "PUT",
    {"value": "Hall"},
)
assert facts["facts"]["preferred_room"] == "Hall"

context = call(f"/sessions/{SESSION}/context?limit=10")
assert context["session"]["messages"][-1]["text"] == "My preferred room is Hall."
assert context["session"]["facts"]["preferred_room"] == "Hall"

cleared = call(f"/sessions/{SESSION}", "DELETE")
assert cleared["removed"] is True

print("ALL SPRINT 8D.1 HALO CONVERSATION MEMORY TESTS PASSED")
'''


def find_project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "services").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


def main() -> int:
    project = find_project()
    main_path = project / "main.py"
    if not main_path.is_file():
        raise SystemExit("main.py not found.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint8d1-conversation-memory-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_path, backup / "main.py")

    service = project / "services" / "halo_conversation_memory_v8"
    if service.exists():
        shutil.copytree(service, backup / "service", dirs_exist_ok=True)
    service.mkdir(parents=True, exist_ok=True)
    (service / "__init__.py").write_text(SERVICE_INIT, encoding="utf-8")
    (service / "store.py").write_text(STORE_PY, encoding="utf-8")
    (service / "routes.py").write_text(ROUTES_PY, encoding="utf-8")

    import_line = (
        "from services.halo_conversation_memory_v8.routes "
        "import router as halo_conversation_memory_v8_router"
    )
    include_line = "app.include_router(halo_conversation_memory_v8_router)"
    text = main_path.read_text(encoding="utf-8", errors="replace")
    additions = []
    if import_line not in text:
        additions.append(import_line)
    if include_line not in text:
        additions.append(include_line)
    if additions:
        main_path.write_text(
            text.rstrip()
            + "\n\n# NOORBRAIN SPRINT 8D.1 CONVERSATION MEMORY\n"
            + "\n".join(additions)
            + "\n",
            encoding="utf-8",
        )

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke_path = tests / "sprint8d1_conversation_memory_smoke_test.py"
    smoke_path.write_text(SMOKE_TEST, encoding="utf-8")

    rollback = project / "installer" / "sprint8" / "rollback_8D1.py"
    rollback.parent.mkdir(parents=True, exist_ok=True)
    rollback.write_text(
        "from pathlib import Path\n"
        "import shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "shutil.copy2(backup / 'main.py', project / 'main.py')\n"
        "service = project / 'services' / 'halo_conversation_memory_v8'\n"
        "if service.exists(): shutil.rmtree(service)\n"
        "if (backup / 'service').exists():\n"
        "    shutil.copytree(backup / 'service', service)\n"
        "print('SPRINT 8D.1 ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = project / "venv" / "bin" / "python"
    subprocess.run(
        [
            str(python), "-m", "py_compile",
            str(Path(__file__).resolve()),
            str(main_path),
            str(service / "store.py"),
            str(service / "routes.py"),
            str(smoke_path),
            str(rollback),
        ],
        check=True,
    )

    print("SPRINT 8D.1 HALO CONVERSATION MEMORY INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
