#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


VERSION = "20260801-1"

INIT_PY = '''from .routes import router

__all__ = ["router"]
'''


ENGINE_PY = r'''from __future__ import annotations

import re
import threading
import time
from typing import Any
from uuid import uuid4

from services.halo_voice_context_v8.engine import voice_context_engine


class UniversalVoiceGateway:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.recent: dict[str, tuple[str, float]] = {}
        self.accepted = 0
        self.duplicates = 0
        self.errors = 0

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def prepare(
        self,
        session_id: str,
        transcript: str,
        source: str,
    ) -> dict[str, Any]:
        clean = self.normalize(transcript)
        normalized = clean.casefold()
        now = time.monotonic()

        with self.lock:
            previous, previous_at = self.recent.get(session_id, ("", 0.0))
            if previous == normalized and now - previous_at < 2.0:
                self.duplicates += 1
                return {
                    "accepted": False,
                    "duplicate": True,
                    "session_id": session_id,
                    "transcript": clean,
                }
            self.recent[session_id] = (normalized, now)
            self.accepted += 1

        context = voice_context_engine.build(session_id, clean, 12)
        return {
            "accepted": True,
            "duplicate": False,
            "request_id": uuid4().hex,
            "session_id": session_id,
            "source": source,
            "transcript": clean,
            "context": context,
        }

    def complete(
        self,
        session_id: str,
        transcript: str,
        response: str,
        source: str,
    ) -> dict[str, Any]:
        return voice_context_engine.remember_exchange(
            session_id,
            self.normalize(transcript),
            self.normalize(response),
            source,
        )

    def record_error(self) -> None:
        with self.lock:
            self.errors += 1

    def status(self) -> dict[str, int]:
        with self.lock:
            return {
                "accepted": self.accepted,
                "duplicates_blocked": self.duplicates,
                "errors": self.errors,
            }


universal_voice_gateway = UniversalVoiceGateway()
'''


ROUTES_PY = r'''from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .engine import universal_voice_gateway


router = APIRouter(
    prefix="/api/universal-voice-v9",
    tags=["Universal Voice Gateway V9"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "universal_voice_gateway_v9",
        "version": "9.1.0",
        "runtime": universal_voice_gateway.status(),
    }


@router.get("/capabilities")
async def capabilities() -> dict[str, Any]:
    return {
        "status": "ready",
        "version": "9.1.0",
        "text_commands": True,
        "browser_speech_recognition": "client-detected",
        "audio_capture": "client-detected",
        "offline_transcription": "foundation",
        "conversation_context": True,
        "duplicate_protection": True,
    }


@router.post("/prepare")
async def prepare(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    transcript = str(payload.get("transcript") or "").strip()
    session_id = str(payload.get("session_id") or "default").strip()
    source = str(payload.get("source") or "text").strip()
    if not transcript:
        raise HTTPException(status_code=422, detail="Transcript is required.")
    try:
        result = await asyncio.to_thread(
            universal_voice_gateway.prepare,
            session_id,
            transcript,
            source,
        )
        return {"status": "ready" if result["accepted"] else "duplicate", **result}
    except Exception as error:
        universal_voice_gateway.record_error()
        raise HTTPException(
            status_code=503,
            detail=f"Voice gateway temporarily unavailable: {type(error).__name__}",
        ) from error


@router.post("/complete")
async def complete(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "default").strip()
    transcript = str(payload.get("transcript") or "").strip()
    response = str(payload.get("response") or "").strip()
    source = str(payload.get("source") or "voice").strip()
    if not transcript or not response:
        raise HTTPException(
            status_code=422,
            detail="Transcript and response are required.",
        )
    try:
        exchange = await asyncio.to_thread(
            universal_voice_gateway.complete,
            session_id,
            transcript,
            response,
            source,
        )
        return {"status": "remembered", "exchange": exchange}
    except Exception as error:
        universal_voice_gateway.record_error()
        raise HTTPException(
            status_code=503,
            detail=f"Voice memory temporarily unavailable: {type(error).__name__}",
        ) from error
'''


GATEWAY_JS = r'''(() => {
  "use strict";

  if (window.NoorBrainUniversalVoice?.installed) return;

  const API = "/api/universal-voice-v9";
  const state = {
    listening: false,
    recognition: null,
    lastTranscript: "",
    lastAt: 0,
  };

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json"},
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `Voice gateway HTTP ${response.status}`);
    return body;
  }

  function capabilities() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    return {
      secure_context: window.isSecureContext,
      browser_recognition: Boolean(Recognition),
      audio_capture: Boolean(navigator.mediaDevices?.getUserMedia),
      speech_output: Boolean(window.speechSynthesis),
    };
  }

  async function send(transcript, options = {}) {
    const clean = String(transcript || "").replace(/\s+/g, " ").trim();
    if (!clean) throw new Error("Please say or type a command.");
    const now = Date.now();
    if (clean.toLowerCase() === state.lastTranscript && now - state.lastAt < 1500) {
      return {status: "duplicate", accepted: false, duplicate: true};
    }
    state.lastTranscript = clean.toLowerCase();
    state.lastAt = now;

    const result = await api("/prepare", {
      method: "POST",
      body: JSON.stringify({
        session_id: options.session_id || localStorage.getItem("noorbrain.voice.session") || "home",
        transcript: clean,
        source: options.source || "browser",
      }),
    });

    if (result.accepted) {
      window.dispatchEvent(new CustomEvent("noorbrain:voice-command-ready", {
        detail: result,
      }));
    }
    return result;
  }

  function listen(options = {}) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      const detail = capabilities().audio_capture
        ? "Audio capture works, but this browser has no live speech recognition."
        : "Microphone is unavailable. Use HTTPS, localhost, or type your command.";
      window.dispatchEvent(new CustomEvent("noorbrain:voice-unavailable", {detail}));
      return Promise.reject(new Error(detail));
    }
    if (state.listening) return Promise.reject(new Error("HALO is already listening."));

    return new Promise((resolve, reject) => {
      const recognition = new Recognition();
      state.recognition = recognition;
      state.listening = true;
      recognition.lang = options.lang || document.documentElement.lang || "en-CA";
      recognition.interimResults = false;
      recognition.continuous = false;

      recognition.onresult = async event => {
        try {
          const transcript = event.results?.[0]?.[0]?.transcript || "";
          resolve(await send(transcript, {...options, source: "browser-speech"}));
        } catch (error) {
          reject(error);
        }
      };
      recognition.onerror = event => reject(new Error(event.error || "Voice recognition failed."));
      recognition.onend = () => {
        state.listening = false;
        state.recognition = null;
      };
      recognition.start();
    });
  }

  function stop() {
    state.recognition?.stop();
    state.listening = false;
  }

  window.NoorBrainUniversalVoice = Object.freeze({
    installed: true,
    version: "9.1.0",
    capabilities,
    send,
    listen,
    stop,
  });
})();
'''


SMOKE_TEST = r'''from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def call(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


health = call("/api/universal-voice-v9/health")
assert health["version"] == "9.1.0"

capabilities = call("/api/universal-voice-v9/capabilities")
assert capabilities["duplicate_protection"] is True
assert capabilities["conversation_context"] is True

first = call(
    "/api/universal-voice-v9/prepare", "POST",
    {"session_id": "sprint9a1-smoke", "transcript": "Turn on the Hall light."},
)
assert first["accepted"] is True
assert "context" in first

second = call(
    "/api/universal-voice-v9/prepare", "POST",
    {"session_id": "sprint9a1-smoke", "transcript": "Turn on the Hall light."},
)
assert second["duplicate"] is True

with urllib.request.urlopen(
    BASE + "/dashboard-static/js/sprint9a1-universal-voice.js?v=20260801-1",
    timeout=30,
) as response:
    script = response.read().decode("utf-8", errors="replace")
assert "NoorBrainUniversalVoice" in script

for page in ("/studio", "/mobile"):
    with urllib.request.urlopen(BASE + page, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    assert "sprint9a1-universal-voice.js?v=20260801-1" in html

print("ALL SPRINT 9A.1 UNIVERSAL VOICE GATEWAY TESTS PASSED")
'''


def find_project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "dashboard").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


def inject(path: Path, asset: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r'\s*<script[^>]+sprint9a1-universal-voice\.js[^>]*></script>',
        "", text, flags=re.IGNORECASE,
    )
    position = text.lower().rfind("</body>")
    if position < 0:
        raise SystemExit(f"Missing </body> in {path}")
    path.write_text(text[:position] + "  " + asset + "\n" + text[position:], encoding="utf-8")


def patch_worker(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r'const CACHE\s*=\s*["\'][^"\']+["\'];',
        'const CACHE = "noorbrain-sprint9a1-universal-voice-v1";',
        text, count=1,
    )
    asset = "/dashboard-static/js/sprint9a1-universal-voice.js?v=20260801-1"
    match = re.search(r"const SHELL\s*=\s*\[", text)
    if match and asset not in text:
        text = text[:match.end()] + f'\n  "{asset}",' + text[match.end():]
    path.write_text(text, encoding="utf-8")


def main() -> int:
    project = find_project()
    main_path = project / "main.py"
    studio = project / "dashboard" / "index.html"
    mobile = project / "dashboard" / "mobile" / "index.html"
    worker = project / "dashboard" / "pwa" / "sw.js"
    context = project / "services" / "halo_voice_context_v8" / "engine.py"
    missing = [str(path) for path in (main_path, studio, mobile, worker, context) if not path.is_file()]
    if missing:
        raise SystemExit("Sprint 8 voice context required. Missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint9a1-universal-voice-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    for source in (main_path, studio, mobile, worker):
        relative = source.relative_to(project)
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    service = project / "services" / "universal_voice_gateway_v9"
    if service.exists():
        shutil.copytree(service, backup / "service", dirs_exist_ok=True)
    service.mkdir(parents=True, exist_ok=True)
    (service / "__init__.py").write_text(INIT_PY, encoding="utf-8")
    (service / "engine.py").write_text(ENGINE_PY, encoding="utf-8")
    (service / "routes.py").write_text(ROUTES_PY, encoding="utf-8")

    js_path = project / "dashboard" / "js" / "sprint9a1-universal-voice.js"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(GATEWAY_JS, encoding="utf-8")
    asset = f'<script src="/dashboard-static/js/sprint9a1-universal-voice.js?v={VERSION}"></script>'
    inject(studio, asset)
    inject(mobile, asset)
    patch_worker(worker)

    text = main_path.read_text(encoding="utf-8", errors="replace")
    import_line = (
        "from services.universal_voice_gateway_v9.routes "
        "import router as universal_voice_gateway_v9_router"
    )
    include_line = "app.include_router(universal_voice_gateway_v9_router)"
    additions = []
    if import_line not in text:
        additions.append(import_line)
    if include_line not in text:
        additions.append(include_line)
    if additions:
        main_path.write_text(
            text.rstrip() + "\n\n# NOORBRAIN SPRINT 9A.1 UNIVERSAL VOICE GATEWAY\n"
            + "\n".join(additions) + "\n",
            encoding="utf-8",
        )

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke = tests / "sprint9a1_universal_voice_smoke_test.py"
    smoke.write_text(SMOKE_TEST, encoding="utf-8")

    rollback = project / "installer" / "sprint9" / "rollback_9A1.py"
    rollback.parent.mkdir(parents=True, exist_ok=True)
    rollback.write_text(
        "from pathlib import Path\nimport shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "for relative in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:\n"
        "    shutil.copy2(backup / relative, project / relative)\n"
        "service = project / 'services/universal_voice_gateway_v9'\n"
        "if service.exists(): shutil.rmtree(service)\n"
        "if (backup / 'service').exists(): shutil.copytree(backup / 'service', service)\n"
        "(project / 'dashboard/js/sprint9a1-universal-voice.js').unlink(missing_ok=True)\n"
        "print('SPRINT 9A.1 ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = project / "venv" / "bin" / "python"
    subprocess.run(
        [str(python), "-m", "py_compile", str(Path(__file__).resolve()),
         str(main_path), str(service / "engine.py"), str(service / "routes.py"),
         str(smoke), str(rollback)],
        check=True,
    )
    print("SPRINT 9A.1 UNIVERSAL VOICE GATEWAY INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
