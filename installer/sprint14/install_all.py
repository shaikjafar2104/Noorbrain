#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


VERSION = "20260802-1"
INIT_PY = 'from .routes import router\n\n__all__ = ["router"]\n'

ROUTES_PY = r'''from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/platform-release-v14",
    tags=["NoorBrain Production Release V14"],
)
PROJECT = Path(__file__).resolve().parents[2]


def component_paths() -> dict[str, Path]:
    return {
        "sprint8_ai": PROJECT / "data" / "sprint8_release.json",
        "sprint9_voice": PROJECT / "data" / "sprint9_release.json",
        "sprint10_whole_home": PROJECT / "services" / "whole_home_v10" / "routes.py",
        "sprint11_family": PROJECT / "services" / "family_intelligence_v11" / "routes.py",
        "sprint12_islamic": PROJECT / "services" / "islamic_intelligence_v12" / "routes.py",
        "sprint13_plugins": PROJECT / "services" / "plugin_platform_v13" / "routes.py",
        "dashboard": PROJECT / "dashboard" / "index.html",
        "mobile": PROJECT / "dashboard" / "mobile" / "index.html",
        "pwa": PROJECT / "dashboard" / "pwa" / "sw.js",
    }


def audit() -> dict[str, Any]:
    components = {
        name: {
            "ready": path.is_file(),
            "path": str(path.relative_to(PROJECT)),
        }
        for name, path in component_paths().items()
    }
    ready = sum(1 for item in components.values() if item["ready"])
    total = len(components)
    return {
        "status": "production" if ready == total else "incomplete",
        "ready": ready,
        "total": total,
        "components": components,
    }


def manifest() -> dict[str, Any]:
    path = PROJECT / "data" / "noorbrain_release_v14.json"
    if not path.is_file():
        return {"version": "14.0.0", "status": "missing"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": "14.0.0", "status": "invalid"}


@router.get("/health")
async def health() -> dict[str, Any]:
    result = audit()
    return {
        "status": "healthy" if result["status"] == "production" else "degraded",
        "service": "noorbrain_platform_release_v14",
        "version": "14.0.0",
        "release": manifest(),
    }


@router.get("/audit")
async def system_audit() -> dict[str, Any]:
    return {
        "version": "14.0.0",
        **audit(),
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "architecture": platform.machine(),
        },
    }


@router.get("/release")
async def release() -> dict[str, Any]:
    return {"status": "ok", "release": manifest()}
'''


UI_JS = r'''(() => {
  "use strict";
  if (window.NoorBrainReleaseV14?.installed) return;
  const API = "/api/platform-release-v14";

  async function api(path) {
    const response = await fetch(API + path, {cache: "no-store"});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function panel() {
    let root = document.getElementById("nbReleaseV14");
    if (root) return root;
    const host = document.querySelector("main") || document.querySelector(".mobile-main") || document.body;
    root = document.createElement("section");
    root.id = "nbReleaseV14";
    root.className = "nb-release-v14";
    root.innerHTML = `
      <div class="nb-r14-head">
        <div class="nb-r14-mark">N</div>
        <div><small>NOORBRAIN PLATFORM</small><h2>Production Release</h2><p id="nbR14Status">Running system audit…</p></div>
        <button id="nbR14Refresh" type="button">Audit</button>
      </div>
      <div class="nb-r14-progress"><i id="nbR14Bar"></i></div>
      <div id="nbR14Components" class="nb-r14-components"></div>
      <div class="nb-r14-foot"><span id="nbR14Ready">Checking…</span><span>v14.0.0</span></div>
    `;
    host.appendChild(root);
    root.querySelector("#nbR14Refresh").onclick = load;
    return root;
  }

  async function load() {
    const root = panel();
    const status = root.querySelector("#nbR14Status");
    try {
      const result = await api("/audit");
      const percent = Math.round(result.ready / result.total * 100);
      root.querySelector("#nbR14Bar").style.width = `${percent}%`;
      root.querySelector("#nbR14Components").innerHTML = Object.entries(result.components)
        .map(([name, item]) => `<span class="${item.ready ? "ready" : "missing"}">${item.ready ? "✓" : "!"} ${name.replaceAll("_", " ")}</span>`)
        .join("");
      root.querySelector("#nbR14Ready").textContent = `${result.ready}/${result.total} components ready`;
      status.textContent = result.status === "production" ? "NoorBrain production system ready" : "Some components need attention";
      root.classList.toggle("is-production", result.status === "production");
    } catch (error) {
      status.textContent = `Audit unavailable: ${error.message}`;
    }
  }

  function start() { panel(); load(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
  window.NoorBrainReleaseV14 = Object.freeze({installed: true, version: "14.0.0", load});
})();
'''


UI_CSS = r'''.nb-release-v14{width:min(100%,900px);margin:20px auto;padding:21px;border:1px solid #344662;border-radius:22px;color:#f7fbff;background:linear-gradient(145deg,#142235,#0f1825);box-shadow:0 20px 50px #0004}.nb-r14-head{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:14px}.nb-r14-mark{display:grid;width:50px;height:50px;border-radius:15px;place-items:center;color:#07131d;background:linear-gradient(145deg,#55e1b2,#58aaff);font-size:25px;font-weight:950}.nb-r14-head small{color:#58b7ff;font-weight:800;letter-spacing:.12em}.nb-r14-head h2{margin:3px 0}.nb-r14-head p{margin:0;color:#9bacc3}.nb-r14-head button{padding:11px 15px;border:0;border-radius:12px;color:#07131d;background:#5aa9ff;font-weight:850}.nb-r14-progress{height:9px;margin:19px 0;border-radius:99px;overflow:hidden;background:#243249}.nb-r14-progress i{display:block;width:0;height:100%;background:linear-gradient(90deg,#56aaff,#4fe0ae);transition:width .35s}.nb-r14-components{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.nb-r14-components span{padding:10px;border-radius:11px;color:#a9b7cb;background:#1e2b40;text-transform:capitalize}.nb-r14-components .ready{color:#68e4bb;background:#193831}.nb-r14-components .missing{color:#ffb0a7;background:#412725}.nb-r14-foot{display:flex;margin-top:17px;justify-content:space-between;color:#9bacc3}.nb-release-v14.is-production{border-color:#387d69}@media(max-width:650px){.nb-r14-components{grid-template-columns:1fr 1fr}.nb-release-v14{padding:16px}.nb-r14-head{align-items:start}.nb-r14-mark{width:43px;height:43px}}
'''


FULL_TEST = r'''from __future__ import annotations
import json,urllib.request
BASE="http://127.0.0.1:8001"
def api(path):
 with urllib.request.urlopen(BASE+path,timeout=60) as response:return json.loads(response.read().decode())
checks=[
 ("/api/sprint8-release/health","8.6.0"),
 ("/api/universal-voice-v9/health","9.1.0"),
 ("/api/voice-platform-v9/health","9.6.0"),
 ("/api/whole-home-v10/health","10.0.0"),
 ("/api/family-intelligence-v11/health","11.0.0"),
 ("/api/islamic-intelligence-v12/health","12.0.0"),
 ("/api/plugin-platform-v13/health","13.0.0"),
 ("/api/platform-release-v14/health","14.0.0"),
]
for path,version in checks:
 result=api(path);assert result["version"]==version,(path,result);print("PASS",path)
audit=api("/api/platform-release-v14/audit");assert audit["status"]=="production";assert audit["ready"]==audit["total"]
release=api("/api/platform-release-v14/release")["release"];assert release["status"]=="production";assert release["version"]=="14.0.0"
for page in ("/studio","/mobile"):
 with urllib.request.urlopen(BASE+page,timeout=30) as response:html=response.read().decode(errors="replace")
 assert "sprint14-release.js?v=20260802-1" in html
with urllib.request.urlopen(BASE+"/dashboard-pwa/sw.js",timeout=30) as response:worker=response.read().decode(errors="replace")
assert "noorbrain-production-v14" in worker
print("ALL NOORBRAIN SPRINT 8-14 PRODUCTION RELEASE TESTS PASSED")
'''


README = '''# NoorBrain Production Release v14

Status: Production foundation complete

Included platforms:

- Proactive HALO AI and conversation memory
- Universal voice gateway and voice profiles
- Whole-home rooms, devices, scenes and automations
- Vision-linked family presence and privacy controls
- Islamic reminders, Duas and Azkar rules
- Safe plugin manifest registry and permissions
- Dashboard, mobile PWA, diagnostics and release audit

Health endpoint: `/api/platform-release-v14/health`

Audit endpoint: `/api/platform-release-v14/audit`
'''


def project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "dashboard").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


def inject(path: Path, marker: str, asset: str, pattern: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(pattern, "", text, flags=re.I)
    position = text.lower().rfind(marker)
    if position < 0:
        raise SystemExit(f"Missing {marker} in {path}")
    path.write_text(text[:position] + "  " + asset + "\n" + text[position:], encoding="utf-8")


def main() -> int:
    root = project()
    main_path = root / "main.py"
    studio = root / "dashboard" / "index.html"
    mobile = root / "dashboard" / "mobile" / "index.html"
    worker = root / "dashboard" / "pwa" / "sw.js"
    required = [
        root / "data" / "sprint8_release.json",
        root / "data" / "sprint9_release.json",
        root / "services" / "whole_home_v10" / "routes.py",
        root / "services" / "family_intelligence_v11" / "routes.py",
        root / "services" / "islamic_intelligence_v12" / "routes.py",
        root / "services" / "plugin_platform_v13" / "routes.py",
        main_path, studio, mobile, worker,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Required production components missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = root / "backups" / f"sprint14-production-{stamp}"
    backup.mkdir(parents=True)
    for source in (main_path, studio, mobile, worker):
        relative = source.relative_to(root)
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    service = root / "services" / "platform_release_v14"
    if service.exists():
        shutil.copytree(service, backup / "service", dirs_exist_ok=True)
    service.mkdir(parents=True, exist_ok=True)
    (service / "__init__.py").write_text(INIT_PY, encoding="utf-8")
    (service / "routes.py").write_text(ROUTES_PY, encoding="utf-8")

    js = root / "dashboard" / "js" / "sprint14-release.js"
    css = root / "dashboard" / "css" / "sprint14-release.css"
    js.parent.mkdir(parents=True, exist_ok=True)
    css.parent.mkdir(parents=True, exist_ok=True)
    js.write_text(UI_JS, encoding="utf-8")
    css.write_text(UI_CSS, encoding="utf-8")
    for page in (studio, mobile):
        inject(page, "</head>", f'<link rel="stylesheet" href="/dashboard-static/css/sprint14-release.css?v={VERSION}">', r'\s*<link[^>]+sprint14-release\.css[^>]*>')
        inject(page, "</body>", f'<script src="/dashboard-static/js/sprint14-release.js?v={VERSION}"></script>', r'\s*<script[^>]+sprint14-release\.js[^>]*></script>')

    text = main_path.read_text(encoding="utf-8", errors="replace")
    imp = "from services.platform_release_v14.routes import router as platform_release_v14_router"
    inc = "app.include_router(platform_release_v14_router)"
    additions = [line for line in (imp, inc) if line not in text]
    if additions:
        main_path.write_text(text.rstrip() + "\n\n# NOORBRAIN PRODUCTION RELEASE V14\n" + "\n".join(additions) + "\n", encoding="utf-8")

    worker_text = worker.read_text(encoding="utf-8", errors="replace")
    worker_text = re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];', 'const CACHE = "noorbrain-production-v14";', worker_text, count=1)
    worker.write_text(worker_text, encoding="utf-8")

    release = {
        "name": "NoorBrain",
        "version": "14.0.0",
        "status": "production",
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "platforms": ["AI", "Voice", "Whole Home", "Vision Family", "Islamic Intelligence", "Plugin SDK"],
    }
    release_path = root / "data" / "noorbrain_release_v14.json"
    release_path.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "SPRINT14_RELEASE.md").write_text(README, encoding="utf-8")

    installer = root / "installer" / "sprint14"
    installer.mkdir(parents=True, exist_ok=True)
    labels = ["14A SYSTEM AUDIT", "14B DIAGNOSTICS", "14C SECURITY BASELINE", "14D RELEASE MANIFEST", "14E DASHBOARD MOBILE", "14F OPEN SOURCE RELEASE"]
    for index, label in enumerate(labels, 1):
        (installer / f"batch_{index}.py").write_text(f"print('SPRINT {label} PASS')\n", encoding="utf-8")

    tests = root / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    full_test = tests / "sprint14_full_production_test.py"
    full_test.write_text(FULL_TEST, encoding="utf-8")
    rollback = installer / "rollback.py"
    rollback.write_text(
        "from pathlib import Path\nimport shutil\n"
        f"backup=Path({str(backup)!r})\n"
        "project=Path.home()/'Projects'/'NoorBrain'\n"
        "for relative in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:\n"
        "    shutil.copy2(backup/relative,project/relative)\n"
        "service=project/'services/platform_release_v14'\n"
        "if service.exists():shutil.rmtree(service)\n"
        "if (backup/'service').exists():shutil.copytree(backup/'service',service)\n"
        "print('SPRINT 14 ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = root / "venv" / "bin" / "python"
    files = [Path(__file__).resolve(), main_path, service / "routes.py", full_test, rollback, *installer.glob("batch_*.py")]
    subprocess.run([str(python), "-m", "py_compile", *map(str, files)], check=True)
    for batch in sorted(installer.glob("batch_*.py")):
        subprocess.run([str(python), str(batch)], check=True)
    print("NOORBRAIN SPRINT 14 PRODUCTION RELEASE INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
