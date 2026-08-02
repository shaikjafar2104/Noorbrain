#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path


INIT_PY = '''from .routes import router

__all__ = ["router"]
'''


ENGINE_PY = r'''from __future__ import annotations

from typing import Any

from services.halo_conversation_memory_v8.store import (
    conversation_memory_store,
)


class VoiceContextEngine:
    def build(
        self,
        session_id: str,
        utterance: str,
        limit: int = 12,
    ) -> dict[str, Any]:
        session = conversation_memory_store.context(session_id, limit)
        messages = session.get("messages", [])
        facts = session.get("facts", {})

        recent = [
            {
                "role": item.get("role", "user"),
                "text": item.get("text", ""),
            }
            for item in messages
            if str(item.get("text") or "").strip()
        ]

        fact_lines = [
            f"{key}: {value}"
            for key, value in sorted(facts.items())
        ]

        system_prompt = (
            "You are HALO, NoorBrain's concise home assistant. "
            "Use remembered context only when relevant. "
            "Never invent a family preference or device state."
        )
        if fact_lines:
            system_prompt += "\nRemembered facts:\n- " + "\n- ".join(fact_lines)

        return {
            "session_id": session_id,
            "utterance": utterance.strip(),
            "system_prompt": system_prompt,
            "recent_messages": recent,
            "facts": facts,
            "message_count": len(recent),
        }

    def remember_exchange(
        self,
        session_id: str,
        user_text: str,
        assistant_text: str,
        source: str = "voice",
    ) -> dict[str, Any]:
        user_message = conversation_memory_store.remember(
            session_id,
            "user",
            user_text,
            {"source": source},
        )
        assistant_message = conversation_memory_store.remember(
            session_id,
            "assistant",
            assistant_text,
            {"source": source},
        )
        return {
            "user_message": user_message,
            "assistant_message": assistant_message,
        }


voice_context_engine = VoiceContextEngine()
'''


ROUTES_PY = r'''from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from .engine import voice_context_engine


router = APIRouter(
    prefix="/api/halo-voice-context-v8",
    tags=["HALO Voice Context V8"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_voice_context_v8",
        "version": "8.4.1",
    }


@router.post("/context")
async def context(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "default").strip()
    utterance = str(payload.get("utterance") or "").strip()
    limit = int(payload.get("limit") or 12)
    if not utterance:
        raise HTTPException(status_code=422, detail="Utterance is required.")
    result = await asyncio.to_thread(
        voice_context_engine.build,
        session_id,
        utterance,
        max(1, min(limit, 50)),
    )
    return {"status": "ok", "context": result}


@router.post("/exchange")
async def exchange(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "default").strip()
    user_text = str(payload.get("user_text") or "").strip()
    assistant_text = str(payload.get("assistant_text") or "").strip()
    source = str(payload.get("source") or "voice").strip()
    if not user_text or not assistant_text:
        raise HTTPException(
            status_code=422,
            detail="User and assistant text are required.",
        )
    remembered = await asyncio.to_thread(
        voice_context_engine.remember_exchange,
        session_id,
        user_text,
        assistant_text,
        source,
    )
    return {"status": "remembered", "exchange": remembered}


@router.get("/sessions/{session_id}/context")
async def session_context(
    session_id: str,
    utterance: str = Query("Continue our conversation."),
    limit: int = Query(12, ge=1, le=50),
) -> dict[str, Any]:
    result = await asyncio.to_thread(
        voice_context_engine.build,
        session_id,
        utterance,
        limit,
    )
    return {"status": "ok", "context": result}
'''


SMOKE_TEST = r'''from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"
SESSION = "sprint8d2-smoke"


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


health = call("/api/halo-voice-context-v8/health")
assert health["version"] == "8.4.1"

call(f"/api/halo-memory-v8/sessions/{SESSION}", "DELETE")

exchange = call(
    "/api/halo-voice-context-v8/exchange",
    "POST",
    {
        "session_id": SESSION,
        "user_text": "Turn on the Hall light.",
        "assistant_text": "The Hall light is on.",
    },
)
assert exchange["status"] == "remembered"

context = call(
    "/api/halo-voice-context-v8/context",
    "POST",
    {
        "session_id": SESSION,
        "utterance": "Turn it off.",
    },
)
assert context["context"]["message_count"] == 2
assert context["context"]["recent_messages"][-1]["role"] == "assistant"
assert context["context"]["utterance"] == "Turn it off."

call(f"/api/halo-memory-v8/sessions/{SESSION}", "DELETE")
print("ALL SPRINT 8D.2 HALO VOICE CONTEXT TESTS PASSED")
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
    memory_service = project / "services" / "halo_conversation_memory_v8"
    if not (memory_service / "store.py").is_file():
        raise SystemExit("Install Sprint 8D.1 first.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint8d2-voice-context-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_path, backup / "main.py")

    service = project / "services" / "halo_voice_context_v8"
    if service.exists():
        shutil.copytree(service, backup / "service", dirs_exist_ok=True)
    service.mkdir(parents=True, exist_ok=True)
    (service / "__init__.py").write_text(INIT_PY, encoding="utf-8")
    (service / "engine.py").write_text(ENGINE_PY, encoding="utf-8")
    (service / "routes.py").write_text(ROUTES_PY, encoding="utf-8")

    import_line = (
        "from services.halo_voice_context_v8.routes "
        "import router as halo_voice_context_v8_router"
    )
    include_line = "app.include_router(halo_voice_context_v8_router)"
    text = main_path.read_text(encoding="utf-8", errors="replace")
    additions = []
    if import_line not in text:
        additions.append(import_line)
    if include_line not in text:
        additions.append(include_line)
    if additions:
        main_path.write_text(
            text.rstrip()
            + "\n\n# NOORBRAIN SPRINT 8D.2 VOICE CONTEXT\n"
            + "\n".join(additions)
            + "\n",
            encoding="utf-8",
        )

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke = tests / "sprint8d2_voice_context_smoke_test.py"
    smoke.write_text(SMOKE_TEST, encoding="utf-8")

    rollback = project / "installer" / "sprint8" / "rollback_8D2.py"
    rollback.parent.mkdir(parents=True, exist_ok=True)
    rollback.write_text(
        "from pathlib import Path\n"
        "import shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "shutil.copy2(backup / 'main.py', project / 'main.py')\n"
        "service = project / 'services' / 'halo_voice_context_v8'\n"
        "if service.exists(): shutil.rmtree(service)\n"
        "if (backup / 'service').exists():\n"
        "    shutil.copytree(backup / 'service', service)\n"
        "print('SPRINT 8D.2 ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = project / "venv" / "bin" / "python"
    subprocess.run(
        [
            str(python), "-m", "py_compile",
            str(Path(__file__).resolve()),
            str(main_path),
            str(service / "engine.py"),
            str(service / "routes.py"),
            str(smoke),
            str(rollback),
        ],
        check=True,
    )

    print("SPRINT 8D.2 HALO VOICE CONTEXT INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
