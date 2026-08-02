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


ROUTES_PY = r'''from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/ai-control-center-v8",
    tags=["AI Control Center V8"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ai_control_center_v8",
        "version": "8.5.0",
    }


@router.get("/overview")
async def overview() -> dict[str, Any]:
    from services.halo_conversation_memory_v8.store import (
        conversation_memory_store,
    )

    memory = await asyncio.to_thread(conversation_memory_store.read)
    sessions = memory.get("sessions", {})
    message_count = sum(
        len(item.get("messages", []))
        for item in sessions.values()
    )
    fact_count = sum(
        len(item.get("facts", {}))
        for item in sessions.values()
    )

    routine = {
        "status": "unavailable",
        "activities": 0,
        "routines": 0,
        "habits": 0,
    }
    try:
        from services.routine_intelligence_v8.routes import health as routine_health
        routine = await routine_health()
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "8.5.0",
        "conversation_memory": {
            "sessions": len(sessions),
            "messages": message_count,
            "facts": fact_count,
        },
        "voice_context": {
            "status": "ready",
            "version": "8.4.1",
        },
        "routine_intelligence": routine,
    }
'''


DASHBOARD_JS = r'''(() => {
  "use strict";

  if (window.NoorBrainAIControlCenter?.installed) return;

  const API = "/api/ai-control-center-v8";

  async function request(path) {
    const response = await fetch(API + path, {cache: "no-store"});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }
    return body;
  }

  function ensurePanel() {
    let panel = document.getElementById("nbAiControlCenterV8");
    if (panel) return panel;

    const host =
      document.querySelector("main") ||
      document.querySelector(".dashboard-main") ||
      document.querySelector(".content") ||
      document.body;

    panel = document.createElement("section");
    panel.id = "nbAiControlCenterV8";
    panel.className = "nb-ai-center";
    panel.innerHTML = `
      <div class="nb-ai-center__head">
        <div>
          <span class="nb-ai-center__eyebrow">HALO Intelligence</span>
          <h2>AI Control Center</h2>
          <p id="nbAiCenterStatus">Loading intelligence…</p>
        </div>
        <button id="nbAiCenterRefresh" type="button">Refresh</button>
      </div>
      <div class="nb-ai-center__grid">
        <article>
          <strong id="nbAiSessions">0</strong>
          <span>Memory sessions</span>
        </article>
        <article>
          <strong id="nbAiMessages">0</strong>
          <span>Remembered messages</span>
        </article>
        <article>
          <strong id="nbAiFacts">0</strong>
          <span>Personal facts</span>
        </article>
        <article>
          <strong id="nbAiActivities">0</strong>
          <span>Routine activities</span>
        </article>
      </div>
      <div class="nb-ai-center__footer">
        <span class="nb-ai-ready">Voice context ready</span>
        <span id="nbAiCenterVersion">v8.5.0</span>
      </div>
    `;

    host.appendChild(panel);
    panel.querySelector("#nbAiCenterRefresh")
      ?.addEventListener("click", refresh);
    return panel;
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = String(value ?? 0);
  }

  async function refresh() {
    const panel = ensurePanel();
    const button = panel.querySelector("#nbAiCenterRefresh");
    const status = panel.querySelector("#nbAiCenterStatus");
    if (button) button.disabled = true;
    if (status) status.textContent = "Refreshing intelligence…";

    try {
      const data = await request("/overview");
      const memory = data.conversation_memory || {};
      const routine = data.routine_intelligence || {};
      setText("nbAiSessions", memory.sessions);
      setText("nbAiMessages", memory.messages);
      setText("nbAiFacts", memory.facts);
      setText("nbAiActivities", routine.activities);
      setText("nbAiCenterVersion", `v${data.version}`);
      if (status) status.textContent = "HALO intelligence is online";
    } catch (error) {
      if (status) status.textContent = `Unavailable: ${error.message}`;
    } finally {
      if (button) button.disabled = false;
    }
  }

  function start() {
    ensurePanel();
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }

  window.NoorBrainAIControlCenter = Object.freeze({
    installed: true,
    version: "8.5.0",
    refresh,
  });
})();
'''


DASHBOARD_CSS = r'''.nb-ai-center {
  margin: 20px 0;
  padding: 22px;
  border: 1px solid rgba(113, 137, 190, .25);
  border-radius: 22px;
  color: #f5f8ff;
  background: linear-gradient(145deg, #141d30, #101827);
  box-shadow: 0 18px 45px rgba(0, 0, 0, .22);
}

.nb-ai-center__head,
.nb-ai-center__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.nb-ai-center__head h2 {
  margin: 3px 0 4px;
  font-size: 24px;
}

.nb-ai-center__head p,
.nb-ai-center__footer {
  margin: 0;
  color: #9eacc7;
}

.nb-ai-center__eyebrow {
  color: #66a8ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.nb-ai-center button {
  padding: 10px 16px;
  border: 0;
  border-radius: 12px;
  color: #08111f;
  background: #5aa9ff;
  font-weight: 800;
  cursor: pointer;
}

.nb-ai-center button:disabled { opacity: .55; }

.nb-ai-center__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 20px 0;
}

.nb-ai-center__grid article {
  display: flex;
  min-height: 92px;
  flex-direction: column;
  justify-content: center;
  padding: 16px;
  border: 1px solid rgba(113, 137, 190, .2);
  border-radius: 16px;
  background: rgba(31, 44, 69, .72);
}

.nb-ai-center__grid strong {
  font-size: 27px;
  color: #ffffff;
}

.nb-ai-center__grid span { color: #9eacc7; }
.nb-ai-ready { color: #4fe0b5; }

@media (max-width: 850px) {
  .nb-ai-center__grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 520px) {
  .nb-ai-center { padding: 17px; border-radius: 18px; }
  .nb-ai-center__head { align-items: flex-start; }
  .nb-ai-center__grid { grid-template-columns: 1fr 1fr; gap: 8px; }
  .nb-ai-center__grid article { min-height: 78px; padding: 12px; }
  .nb-ai-center__grid strong { font-size: 22px; }
}
'''


SMOKE_TEST = r'''from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> tuple[str, str]:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return response.headers.get("content-type", ""), response.read().decode(
            "utf-8", errors="replace"
        )


_, raw = get("/api/ai-control-center-v8/health")
health = json.loads(raw)
assert health["version"] == "8.5.0"

_, raw = get("/api/ai-control-center-v8/overview")
overview = json.loads(raw)
assert "conversation_memory" in overview
assert "voice_context" in overview
assert "routine_intelligence" in overview

_, script = get("/dashboard-static/js/sprint8e1-ai-dashboard.js?v=20260801-1")
assert "NoorBrainAIControlCenter" in script

_, style = get("/dashboard-static/css/sprint8e1-ai-dashboard.css?v=20260801-1")
assert ".nb-ai-center" in style

_, studio = get("/studio")
assert "sprint8e1-ai-dashboard.js?v=20260801-1" in studio
assert "sprint8e1-ai-dashboard.css?v=20260801-1" in studio

print("ALL SPRINT 8E.1 AI DASHBOARD TESTS PASSED")
'''


def find_project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "dashboard").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


def inject(path: Path, marker: str, asset: str, pattern: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    position = text.lower().rfind(marker.lower())
    if position < 0:
        raise SystemExit(f"Missing {marker} in {path}")
    path.write_text(text[:position] + "  " + asset + "\n" + text[position:], encoding="utf-8")


def main() -> int:
    project = find_project()
    main_path = project / "main.py"
    studio = project / "dashboard" / "index.html"
    memory = project / "services" / "halo_conversation_memory_v8" / "store.py"
    voice = project / "services" / "halo_voice_context_v8" / "engine.py"
    missing = [str(p) for p in (main_path, studio, memory, voice) if not p.is_file()]
    if missing:
        raise SystemExit("Install Sprint 8D.1 and 8D.2 first. Missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint8e1-ai-dashboard-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_path, backup / "main.py")
    shutil.copy2(studio, backup / "index.html")

    service = project / "services" / "ai_control_center_v8"
    if service.exists():
        shutil.copytree(service, backup / "service", dirs_exist_ok=True)
    service.mkdir(parents=True, exist_ok=True)
    (service / "__init__.py").write_text(INIT_PY, encoding="utf-8")
    (service / "routes.py").write_text(ROUTES_PY, encoding="utf-8")

    js_path = project / "dashboard" / "js" / "sprint8e1-ai-dashboard.js"
    css_path = project / "dashboard" / "css" / "sprint8e1-ai-dashboard.css"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(DASHBOARD_JS, encoding="utf-8")
    css_path.write_text(DASHBOARD_CSS, encoding="utf-8")

    text = main_path.read_text(encoding="utf-8", errors="replace")
    import_line = (
        "from services.ai_control_center_v8.routes "
        "import router as ai_control_center_v8_router"
    )
    include_line = "app.include_router(ai_control_center_v8_router)"
    additions = []
    if import_line not in text:
        additions.append(import_line)
    if include_line not in text:
        additions.append(include_line)
    if additions:
        main_path.write_text(
            text.rstrip() + "\n\n# NOORBRAIN SPRINT 8E.1 AI DASHBOARD\n"
            + "\n".join(additions) + "\n",
            encoding="utf-8",
        )

    inject(
        studio,
        "</head>",
        f'<link rel="stylesheet" href="/dashboard-static/css/sprint8e1-ai-dashboard.css?v={VERSION}">',
        r'\s*<link[^>]+sprint8e1-ai-dashboard\.css[^>]*>',
    )
    inject(
        studio,
        "</body>",
        f'<script src="/dashboard-static/js/sprint8e1-ai-dashboard.js?v={VERSION}"></script>',
        r'\s*<script[^>]+sprint8e1-ai-dashboard\.js[^>]*></script>',
    )

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke = tests / "sprint8e1_ai_dashboard_smoke_test.py"
    smoke.write_text(SMOKE_TEST, encoding="utf-8")

    rollback = project / "installer" / "sprint8" / "rollback_8E1.py"
    rollback.parent.mkdir(parents=True, exist_ok=True)
    rollback.write_text(
        "from pathlib import Path\nimport shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "shutil.copy2(backup / 'main.py', project / 'main.py')\n"
        "shutil.copy2(backup / 'index.html', project / 'dashboard' / 'index.html')\n"
        "service = project / 'services' / 'ai_control_center_v8'\n"
        "if service.exists(): shutil.rmtree(service)\n"
        "if (backup / 'service').exists(): shutil.copytree(backup / 'service', service)\n"
        "(project / 'dashboard/js/sprint8e1-ai-dashboard.js').unlink(missing_ok=True)\n"
        "(project / 'dashboard/css/sprint8e1-ai-dashboard.css').unlink(missing_ok=True)\n"
        "print('SPRINT 8E.1 ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = project / "venv" / "bin" / "python"
    subprocess.run(
        [str(python), "-m", "py_compile", str(Path(__file__).resolve()),
         str(main_path), str(service / "routes.py"), str(smoke), str(rollback)],
        check=True,
    )
    print("SPRINT 8E.1 AI DASHBOARD CONTROL CENTER INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
