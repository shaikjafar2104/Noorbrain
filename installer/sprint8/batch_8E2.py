#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


VERSION = "20260801-1"


MOBILE_JS = r'''(() => {
  "use strict";

  if (window.NoorBrainMobileAI?.installed) return;

  const API = "/api/ai-control-center-v8";

  async function request(path) {
    const response = await fetch(API + path, {cache: "no-store"});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = String(value ?? 0);
  }

  function ensurePanel() {
    let panel = document.getElementById("nbMobileAiCenterV8");
    if (panel) return panel;

    const host =
      document.querySelector(".mobile-main") ||
      document.querySelector("main") ||
      document.querySelector("#app") ||
      document.body;

    panel = document.createElement("section");
    panel.id = "nbMobileAiCenterV8";
    panel.className = "nb-mobile-ai";
    panel.innerHTML = `
      <div class="nb-mobile-ai__hero">
        <div class="nb-mobile-ai__orb" aria-hidden="true"></div>
        <div>
          <span>HALO INTELLIGENCE</span>
          <h2>AI Control Center</h2>
          <p id="nbMobileAiStatus">Loading your home intelligence…</p>
        </div>
        <button id="nbMobileAiRefresh" type="button" aria-label="Refresh AI center">↻</button>
      </div>
      <div class="nb-mobile-ai__grid">
        <button type="button" data-ai-target="memory">
          <strong id="nbMobileAiSessions">0</strong>
          <span>Memory</span>
          <small id="nbMobileAiMessages">0 messages</small>
        </button>
        <button type="button" data-ai-target="routines">
          <strong id="nbMobileAiActivities">0</strong>
          <span>Activities</span>
          <small id="nbMobileAiHabits">0 habits</small>
        </button>
        <button type="button" data-ai-target="voice">
          <strong>Ready</strong>
          <span>Voice context</span>
          <small>Conversation aware</small>
        </button>
        <button type="button" data-ai-target="facts">
          <strong id="nbMobileAiFacts">0</strong>
          <span>Personal facts</span>
          <small>Private memory</small>
        </button>
      </div>
      <div class="nb-mobile-ai__footer">
        <span class="nb-mobile-ai__live">● AI online</span>
        <span id="nbMobileAiVersion">v8.5.0</span>
      </div>
    `;

    const firstCard = host.querySelector("section, .mobile-card, .card");
    if (firstCard) {
      firstCard.insertAdjacentElement("beforebegin", panel);
    } else {
      host.appendChild(panel);
    }

    panel.querySelector("#nbMobileAiRefresh")
      ?.addEventListener("click", refresh);
    panel.querySelectorAll("[data-ai-target]").forEach(button => {
      button.addEventListener("click", () => {
        panel.querySelectorAll("[data-ai-target]")
          .forEach(item => item.classList.remove("is-selected"));
        button.classList.add("is-selected");
      });
    });
    return panel;
  }

  async function refresh() {
    const panel = ensurePanel();
    const status = panel.querySelector("#nbMobileAiStatus");
    const button = panel.querySelector("#nbMobileAiRefresh");
    if (button) button.disabled = true;
    if (status) status.textContent = "Refreshing intelligence…";

    try {
      const data = await request("/overview");
      const memory = data.conversation_memory || {};
      const routine = data.routine_intelligence || {};
      setText("nbMobileAiSessions", memory.sessions);
      setText("nbMobileAiMessages", `${memory.messages || 0} messages`);
      setText("nbMobileAiFacts", memory.facts);
      setText("nbMobileAiActivities", routine.activities);
      setText("nbMobileAiHabits", `${routine.habits || 0} habits`);
      setText("nbMobileAiVersion", `v${data.version}`);
      if (status) status.textContent = "Your home intelligence is ready";
      panel.classList.add("is-online");
    } catch (error) {
      if (status) status.textContent = `AI unavailable: ${error.message}`;
      panel.classList.remove("is-online");
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

  window.NoorBrainMobileAI = Object.freeze({
    installed: true,
    version: "8.5.1",
    refresh,
  });
})();
'''


MOBILE_CSS = r'''.nb-mobile-ai {
  width: min(100%, 780px);
  margin: 16px auto;
  padding: 18px;
  border: 1px solid rgba(105, 130, 190, .27);
  border-radius: 24px;
  color: #f6f8ff;
  background: linear-gradient(145deg, #16233a, #10182a);
  box-shadow: 0 18px 42px rgba(0, 0, 0, .25);
}

.nb-mobile-ai__hero {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 13px;
}

.nb-mobile-ai__orb {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: radial-gradient(circle at 34% 30%, #b8f4ff, #5baaff 35%, #7658ef 72%);
  box-shadow: 0 0 0 7px rgba(91, 170, 255, .08), 0 0 28px rgba(91, 170, 255, .38);
}

.nb-mobile-ai__hero span {
  color: #70adff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .13em;
}

.nb-mobile-ai__hero h2 { margin: 3px 0; font-size: 21px; }
.nb-mobile-ai__hero p { margin: 0; color: #9baac6; font-size: 13px; }

.nb-mobile-ai__hero button {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 13px;
  color: #dceaff;
  background: #273957;
  font-size: 22px;
  cursor: pointer;
}

.nb-mobile-ai__hero button:disabled { opacity: .5; }

.nb-mobile-ai__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 17px 0;
}

.nb-mobile-ai__grid button {
  display: flex;
  min-height: 112px;
  padding: 14px;
  border: 1px solid rgba(105, 130, 190, .2);
  border-radius: 18px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  text-align: left;
  color: inherit;
  background: rgba(31, 46, 75, .75);
  cursor: pointer;
}

.nb-mobile-ai__grid button.is-selected {
  border-color: #64aaff;
  background: rgba(47, 78, 126, .9);
}

.nb-mobile-ai__grid strong { font-size: 22px; }
.nb-mobile-ai__grid span { margin: 4px 0; font-weight: 750; }
.nb-mobile-ai__grid small { color: #95a5c2; }

.nb-mobile-ai__footer {
  display: flex;
  justify-content: space-between;
  color: #95a5c2;
  font-size: 12px;
}

.nb-mobile-ai__live { color: #50dbad; }

@media (max-width: 430px) {
  .nb-mobile-ai { padding: 15px; border-radius: 20px; }
  .nb-mobile-ai__orb { width: 42px; height: 42px; }
  .nb-mobile-ai__grid { gap: 8px; }
  .nb-mobile-ai__grid button { min-height: 98px; padding: 12px; }
}
'''


SMOKE_TEST = r'''from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


overview = json.loads(get("/api/ai-control-center-v8/overview"))
assert overview["version"] == "8.5.0"

script = get("/dashboard-static/js/sprint8e2-mobile-ai.js?v=20260801-1")
assert "NoorBrainMobileAI" in script
assert "nbMobileAiCenterV8" in script

style = get("/dashboard-static/css/sprint8e2-mobile-ai.css?v=20260801-1")
assert ".nb-mobile-ai" in style

mobile = get("/mobile")
assert "sprint8e2-mobile-ai.js?v=20260801-1" in mobile
assert "sprint8e2-mobile-ai.css?v=20260801-1" in mobile

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-sprint8e2-mobile-ai-v1" in worker
assert "/dashboard-static/js/sprint8e2-mobile-ai.js?v=20260801-1" in worker

print("ALL SPRINT 8E.2 MOBILE AI CONTROL CENTER TESTS PASSED")
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


def patch_worker(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r'const CACHE\s*=\s*["\'][^"\']+["\'];',
        'const CACHE = "noorbrain-sprint8e2-mobile-ai-v1";',
        text,
        count=1,
    )
    assets = [
        "/dashboard-static/js/sprint8e2-mobile-ai.js?v=20260801-1",
        "/dashboard-static/css/sprint8e2-mobile-ai.css?v=20260801-1",
    ]
    match = re.search(r"const SHELL\s*=\s*\[", text)
    if match:
        additions = "".join(
            f'\n  "{asset}",' for asset in assets if asset not in text
        )
        text = text[:match.end()] + additions + text[match.end():]
    path.write_text(text, encoding="utf-8")


def main() -> int:
    project = find_project()
    mobile = project / "dashboard" / "mobile" / "index.html"
    worker = project / "dashboard" / "pwa" / "sw.js"
    api = project / "services" / "ai_control_center_v8" / "routes.py"
    missing = [str(path) for path in (mobile, worker, api) if not path.is_file()]
    if missing:
        raise SystemExit("Install Sprint 8E.1 first. Missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint8e2-mobile-ai-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mobile, backup / "index.html")
    shutil.copy2(worker, backup / "sw.js")

    js_path = project / "dashboard" / "js" / "sprint8e2-mobile-ai.js"
    css_path = project / "dashboard" / "css" / "sprint8e2-mobile-ai.css"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(MOBILE_JS, encoding="utf-8")
    css_path.write_text(MOBILE_CSS, encoding="utf-8")

    inject(
        mobile, "</head>",
        f'<link rel="stylesheet" href="/dashboard-static/css/sprint8e2-mobile-ai.css?v={VERSION}">',
        r'\s*<link[^>]+sprint8e2-mobile-ai\.css[^>]*>',
    )
    inject(
        mobile, "</body>",
        f'<script src="/dashboard-static/js/sprint8e2-mobile-ai.js?v={VERSION}"></script>',
        r'\s*<script[^>]+sprint8e2-mobile-ai\.js[^>]*></script>',
    )
    patch_worker(worker)

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke = tests / "sprint8e2_mobile_ai_smoke_test.py"
    smoke.write_text(SMOKE_TEST, encoding="utf-8")

    rollback = project / "installer" / "sprint8" / "rollback_8E2.py"
    rollback.parent.mkdir(parents=True, exist_ok=True)
    rollback.write_text(
        "from pathlib import Path\nimport shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "shutil.copy2(backup / 'index.html', project / 'dashboard/mobile/index.html')\n"
        "shutil.copy2(backup / 'sw.js', project / 'dashboard/pwa/sw.js')\n"
        "(project / 'dashboard/js/sprint8e2-mobile-ai.js').unlink(missing_ok=True)\n"
        "(project / 'dashboard/css/sprint8e2-mobile-ai.css').unlink(missing_ok=True)\n"
        "print('SPRINT 8E.2 ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = project / "venv" / "bin" / "python"
    subprocess.run(
        [str(python), "-m", "py_compile", str(Path(__file__).resolve()),
         str(smoke), str(rollback)],
        check=True,
    )
    print("SPRINT 8E.2 MOBILE AI CONTROL CENTER INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
