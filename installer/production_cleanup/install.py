#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


VERSION = "20260802-1"


CLEANUP_JS = r'''(() => {
  "use strict";

  if (window.NoorBrainProductionCleanup?.installed) return;

  const hiddenClass = "nb-production-hidden";
  let running = false;

  function text(element) {
    return String(element?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function cardFor(element) {
    return element?.closest?.(
      "section, article, .mobile-card, .card, [class*='camera-card'], " +
      "[class*='camera-panel'], [class*='product-card'], [class*='panel']"
    ) || null;
  }

  function hide(element, reason) {
    if (!element || element.dataset.nbProductionHidden === "1") return false;
    element.dataset.nbProductionHidden = "1";
    element.dataset.nbProductionReason = reason;
    element.classList.add(hiddenClass);
    element.setAttribute("aria-hidden", "true");
    return true;
  }

  function hideBrokenDuplicateCamera() {
    const workingCameraExists = [...document.querySelectorAll("section, article, div")]
      .some(element => {
        const value = text(element);
        return (
          value.includes("Camera & Vision Product") ||
          (value.includes("Primary Camera") && value.includes("Reconnect"))
        );
      });

    if (!workingCameraExists) return 0;

    let hidden = 0;
    const candidates = [...document.querySelectorAll("section, article, div")]
      .filter(element => {
        const value = text(element);
        return (
          value.includes("Hall Camera unavailable") &&
          value.includes("Camera 2") &&
          value.includes("Camera 6") &&
          !value.includes("Camera & Vision Product") &&
          !value.includes("Primary Camera")
        );
      })
      .sort((left, right) => text(left).length - text(right).length);

    const duplicate = candidates[0];
    if (duplicate) {
      const card = cardFor(duplicate) || duplicate;
      if (hide(card, "stale-duplicate-camera")) hidden += 1;
    }
    return hidden;
  }

  function hideSprintLabels() {
    let hidden = 0;
    const pattern = /^SPRINT\s+(?:\d+|[A-Z]\d+)(?:[A-Z0-9. -]*)?$/i;
    for (const element of document.querySelectorAll("small, span, label, p, div")) {
      if (element.children.length > 1) continue;
      const value = text(element);
      if (value.length <= 38 && pattern.test(value)) {
        if (hide(element, "developer-sprint-label")) hidden += 1;
      }
    }
    return hidden;
  }

  function hideSmokeActivityCards() {
    let hidden = 0;
    for (const element of document.querySelectorAll("article, li, [class*='activity'] > div")) {
      const value = text(element);
      if (/^Smoke Activity\b/i.test(value) || value.includes("Smoke Activity hall")) {
        if (hide(element, "smoke-test-activity")) hidden += 1;
      }
    }

    for (const element of document.querySelectorAll("strong, b, h3, h4")) {
      if (text(element) !== "Smoke Activity") continue;
      const card = element.closest("article, li, [class*='activity-card'], [class*='timeline'] > div");
      if (hide(card, "smoke-test-activity")) hidden += 1;
    }
    return hidden;
  }

  function renameDeveloperTitles() {
    const replacements = new Map([
      ["Camera & Vision Product", "Camera & Vision"],
      ["Routine Intelligence Product", "Routine Intelligence"],
      ["Mobile AI Control Center", "AI Control Center"],
    ]);
    let renamed = 0;
    for (const element of document.querySelectorAll("h1, h2, h3, h4")) {
      const replacement = replacements.get(text(element));
      if (replacement) {
        element.textContent = replacement;
        renamed += 1;
      }
    }
    return renamed;
  }

  function removeEmptyRecentActivity() {
    for (const heading of document.querySelectorAll("h1, h2, h3, h4")) {
      if (text(heading) !== "Recent Activity") continue;
      const card = cardFor(heading);
      if (!card) continue;
      const visibleItems = [...card.querySelectorAll("article, li, [class*='activity'] > div")]
        .filter(item => !item.classList.contains(hiddenClass));
      if (visibleItems.length === 0) hide(card, "empty-test-activity-section");
    }
  }

  function clean() {
    if (running) return;
    running = true;
    try {
      const result = {
        cameras: hideBrokenDuplicateCamera(),
        sprintLabels: hideSprintLabels(),
        smokeActivities: hideSmokeActivityCards(),
        renamed: renameDeveloperTitles(),
      };
      removeEmptyRecentActivity();
      window.dispatchEvent(new CustomEvent("noorbrain:production-ui-cleaned", {
        detail: result,
      }));
    } finally {
      running = false;
    }
  }

  let timer = 0;
  const observer = new MutationObserver(() => {
    clearTimeout(timer);
    timer = window.setTimeout(clean, 80);
  });

  function start() {
    clean();
    observer.observe(document.body, {childList: true, subtree: true});
    window.setTimeout(clean, 500);
    window.setTimeout(clean, 1800);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }

  window.NoorBrainProductionCleanup = Object.freeze({
    installed: true,
    version: "1.0.0",
    clean,
  });
})();
'''


CLEANUP_CSS = r'''.nb-production-hidden {
  display: none !important;
  visibility: hidden !important;
}

body.nb-production-ui [data-nb-production-reason="developer-sprint-label"] {
  display: none !important;
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
    "/dashboard-static/js/production-ui-cleanup.js?v=20260802-1"
)
assert "NoorBrainProductionCleanup" in script
assert "stale-duplicate-camera" in script
assert "developer-sprint-label" in script
assert "smoke-test-activity" in script
assert "Camera & Vision Product" in script

style = get(
    "/dashboard-static/css/production-ui-cleanup.css?v=20260802-1"
)
assert ".nb-production-hidden" in style

for page in ("/studio", "/mobile"):
    html = get(page)
    assert "production-ui-cleanup.js?v=20260802-1" in html
    assert "production-ui-cleanup.css?v=20260802-1" in html

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-production-ui-cleanup-v1" in worker
assert "production-ui-cleanup.js?v=20260802-1" in worker

print("ALL NOORBRAIN PRODUCTION UI CLEANUP TESTS PASSED")
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
        'const CACHE = "noorbrain-production-ui-cleanup-v1";',
        content,
        count=1,
    )
    assets = [
        "/dashboard-static/js/production-ui-cleanup.js?v=20260802-1",
        "/dashboard-static/css/production-ui-cleanup.css?v=20260802-1",
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
    required = [studio, mobile, worker]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Required UI files missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"production-ui-cleanup-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    for source in required:
        relative = source.relative_to(project)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    js_path = project / "dashboard" / "js" / "production-ui-cleanup.js"
    css_path = project / "dashboard" / "css" / "production-ui-cleanup.css"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(CLEANUP_JS, encoding="utf-8")
    css_path.write_text(CLEANUP_CSS, encoding="utf-8")

    for page in (studio, mobile):
        inject(
            page,
            "</head>",
            f'<link rel="stylesheet" href="/dashboard-static/css/production-ui-cleanup.css?v={VERSION}">',
            r'\s*<link[^>]+production-ui-cleanup\.css[^>]*>',
        )
        inject(
            page,
            "</body>",
            f'<script src="/dashboard-static/js/production-ui-cleanup.js?v={VERSION}"></script>',
            r'\s*<script[^>]+production-ui-cleanup\.js[^>]*></script>',
        )

    patch_worker(worker)

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke = tests / "production_ui_cleanup_smoke_test.py"
    smoke.write_text(SMOKE_TEST, encoding="utf-8")

    installer = project / "installer" / "production_cleanup"
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
        "(project / 'dashboard/js/production-ui-cleanup.js').unlink(missing_ok=True)\n"
        "(project / 'dashboard/css/production-ui-cleanup.css').unlink(missing_ok=True)\n"
        "print('PRODUCTION UI CLEANUP ROLLBACK COMPLETE')\n",
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
    print("NOORBRAIN PRODUCTION UI CLEANUP INSTALLED")
    print("Working Camera & Vision panel preserved")
    print("Broken duplicate camera hidden")
    print("Sprint labels and smoke activities hidden")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
