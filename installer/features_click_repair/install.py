#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


VERSION = "20260802-2"


REPAIR_JS = r'''(() => {
  "use strict";

  if (window.NoorBrainFeatureClickRepair?.installed) return;

  const panels = {
    ai: ["nbMobileAiCenterV8", "nbAiControlCenterV8"],
    voice: ["nbVoicePlatformV9"],
    home: ["nbWholeHomeV10"],
    family: ["nbFamilyV11"],
    islamic: ["nbIslamicV12"],
    plugins: ["nbPluginsV13"],
    system: ["nbReleaseV14"],
  };

  function mobile() {
    return location.pathname.startsWith("/mobile") ||
      matchMedia("(max-width: 760px)").matches;
  }

  function hubParts() {
    const hub = document.getElementById("nbUnifiedHub");
    return {
      hub,
      menu: hub?.querySelector("#nbUhMenu"),
      stage: hub?.querySelector("#nbUhStage"),
      close: hub?.querySelector("#nbUhClose"),
    };
  }

  function findPanel(key) {
    const ids = panels[key] || [];
    if (key === "ai") {
      const preferred = document.getElementById(
        mobile() ? "nbMobileAiCenterV8" : "nbAiControlCenterV8"
      );
      if (preferred) return preferred;
    }
    for (const id of ids) {
      const element = document.getElementById(id);
      if (element) return element;
    }
    return null;
  }

  function showMessage(stage, message) {
    let notice = document.getElementById("nbFeatureRepairNotice");
    if (!notice) {
      notice = document.createElement("div");
      notice.id = "nbFeatureRepairNotice";
      notice.className = "nb-feature-repair-notice";
      stage.appendChild(notice);
    }
    notice.textContent = message;
    notice.hidden = false;
  }

  function open(key, retry = true) {
    window.NoorBrainUnifiedUI?.refresh?.();
    const {hub, menu, stage, close} = hubParts();
    if (!hub || !menu || !stage || !close) return false;

    let panel = findPanel(key);
    if (!panel && retry) {
      showMessage(stage, "Loading feature…");
      stage.hidden = false;
      menu.hidden = true;
      close.hidden = false;
      window.setTimeout(() => open(key, false), 350);
      return true;
    }

    if (!panel) {
      showMessage(stage, "This feature is not installed yet.");
      stage.hidden = false;
      menu.hidden = true;
      close.hidden = false;
      return false;
    }

    const notice = document.getElementById("nbFeatureRepairNotice");
    if (notice) notice.hidden = true;

    if (panel.parentElement !== stage) stage.appendChild(panel);

    stage.querySelectorAll(".nb-unified-panel, [data-nb-unified-feature]")
      .forEach(item => {
        item.hidden = true;
        item.style.setProperty("display", "none", "important");
      });

    panel.dataset.nbUnifiedFeature = key;
    panel.classList.add("nb-unified-panel");
    panel.classList.remove("nb-production-hidden", "nb-unified-duplicate");
    panel.removeAttribute("aria-hidden");
    panel.hidden = false;
    panel.style.setProperty("display", "block", "important");

    stage.hidden = false;
    stage.style.setProperty("display", "block", "important");
    menu.hidden = true;
    menu.style.setProperty("display", "none", "important");
    close.hidden = false;
    close.style.removeProperty("display");
    hub.dataset.openFeature = key;

    window.setTimeout(() => {
      panel.scrollIntoView({behavior: "smooth", block: "start"});
    }, 40);
    return true;
  }

  function close() {
    const {hub, menu, stage, close: closeButton} = hubParts();
    if (!hub || !menu || !stage || !closeButton) return;

    stage.querySelectorAll(".nb-unified-panel, [data-nb-unified-feature]")
      .forEach(item => {
        item.hidden = true;
        item.style.setProperty("display", "none", "important");
      });

    stage.hidden = true;
    stage.style.setProperty("display", "none", "important");
    menu.hidden = false;
    menu.style.removeProperty("display");
    closeButton.hidden = true;
    closeButton.style.setProperty("display", "none", "important");
    delete hub.dataset.openFeature;
    hub.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function handleClick(event) {
    const featureButton = event.target.closest?.("[data-nb-feature]");
    if (featureButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      open(featureButton.dataset.nbFeature);
      return;
    }

    const closeButton = event.target.closest?.("#nbUhClose");
    if (closeButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      close();
    }
  }

  document.addEventListener("click", handleClick, true);
  document.addEventListener("touchend", event => {
    const button = event.target.closest?.("[data-nb-feature], #nbUhClose");
    if (!button) return;
    event.preventDefault();
    if (button.matches("#nbUhClose")) close();
    else open(button.dataset.nbFeature);
  }, {capture: true, passive: false});

  window.NoorBrainFeatureClickRepair = Object.freeze({
    installed: true,
    version: "1.0.0",
    open,
    close,
  });
})();
'''


REPAIR_CSS = r'''#nbUhMenu [data-nb-feature],
#nbUhClose {
  position: relative;
  z-index: 5;
  pointer-events: auto !important;
  touch-action: manipulation;
  cursor: pointer;
  user-select: none;
}

#nbUhStage[hidden],
#nbUhMenu[hidden],
#nbUhClose[hidden],
.nb-unified-panel[hidden] {
  display: none !important;
}

.nb-feature-repair-notice {
  padding: 28px;
  border: 1px dashed #3b4d6b;
  border-radius: 15px;
  color: #a8b5ca;
  text-align: center;
  background: #172238;
}
'''


SMOKE_TEST = r'''from __future__ import annotations

import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


script = get(
    "/dashboard-static/js/features-click-repair.js?v=20260802-2"
)
assert "NoorBrainFeatureClickRepair" in script
assert "data-nb-feature" in script
assert "touchend" in script
assert "stopImmediatePropagation" in script
assert "nbWholeHomeV10" in script
assert "nbFamilyV11" in script
assert "nbIslamicV12" in script

style = get(
    "/dashboard-static/css/features-click-repair.css?v=20260802-2"
)
assert "touch-action: manipulation" in style

for page in ("/studio", "/mobile"):
    html = get(page)
    assert "features-click-repair.js?v=20260802-2" in html
    assert "features-click-repair.css?v=20260802-2" in html

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-features-click-repair-v2" in worker

print("ALL NOORBRAIN FEATURES CLICK REPAIR TESTS PASSED")
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
    content = path.read_text(encoding="utf-8", errors="replace")
    content = re.sub(pattern, "", content, flags=re.I)
    position = content.lower().rfind(marker)
    if position < 0:
        raise SystemExit(f"Missing {marker} in {path}")
    path.write_text(
        content[:position] + "  " + asset + "\n" + content[position:],
        encoding="utf-8",
    )


def patch_worker(path: Path) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    content = re.sub(
        r'const CACHE\s*=\s*["\'][^"\']+["\'];',
        'const CACHE = "noorbrain-features-click-repair-v2";',
        content,
        count=1,
    )
    assets = [
        "/dashboard-static/js/features-click-repair.js?v=20260802-2",
        "/dashboard-static/css/features-click-repair.css?v=20260802-2",
    ]
    match = re.search(r"const SHELL\s*=\s*\[", content)
    if match:
        additions = "".join(
            f'\n  "{asset}",' for asset in assets if asset not in content
        )
        content = content[:match.end()] + additions + content[match.end():]
    path.write_text(content, encoding="utf-8")


def main() -> int:
    project = find_project()
    studio = project / "dashboard" / "index.html"
    mobile = project / "dashboard" / "mobile" / "index.html"
    worker = project / "dashboard" / "pwa" / "sw.js"
    unified = project / "dashboard" / "js" / "unified-product-ui.js"
    required = [studio, mobile, worker, unified]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(
            "Install Unified Product UI first. Missing:\n"
            + "\n".join(missing)
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"features-click-repair-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    for source in (studio, mobile, worker):
        relative = source.relative_to(project)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    js_path = project / "dashboard" / "js" / "features-click-repair.js"
    css_path = project / "dashboard" / "css" / "features-click-repair.css"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(REPAIR_JS, encoding="utf-8")
    css_path.write_text(REPAIR_CSS, encoding="utf-8")

    for page in (studio, mobile):
        inject(
            page,
            "</head>",
            f'<link rel="stylesheet" href="/dashboard-static/css/features-click-repair.css?v={VERSION}">',
            r'\s*<link[^>]+features-click-repair\.css[^>]*>',
        )
        inject(
            page,
            "</body>",
            f'<script src="/dashboard-static/js/features-click-repair.js?v={VERSION}"></script>',
            r'\s*<script[^>]+features-click-repair\.js[^>]*></script>',
        )

    patch_worker(worker)

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke = tests / "features_click_repair_smoke_test.py"
    smoke.write_text(SMOKE_TEST, encoding="utf-8")

    installer = project / "installer" / "features_click_repair"
    installer.mkdir(parents=True, exist_ok=True)
    rollback = installer / "rollback.py"
    rollback.write_text(
        "from pathlib import Path\nimport shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "for relative in [\n"
        "    'dashboard/index.html',\n"
        "    'dashboard/mobile/index.html',\n"
        "    'dashboard/pwa/sw.js',\n"
        "]:\n"
        "    shutil.copy2(backup / relative, project / relative)\n"
        "(project / 'dashboard/js/features-click-repair.js').unlink(missing_ok=True)\n"
        "(project / 'dashboard/css/features-click-repair.css').unlink(missing_ok=True)\n"
        "print('FEATURES CLICK REPAIR ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = project / "venv" / "bin" / "python"
    subprocess.run(
        [
            str(python), "-m", "py_compile",
            str(Path(__file__).resolve()), str(smoke), str(rollback),
        ],
        check=True,
    )
    print("NOORBRAIN FEATURES CLICK REPAIR INSTALLED")
    print("MOBILE TOUCH AND DESKTOP CLICK ENABLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
