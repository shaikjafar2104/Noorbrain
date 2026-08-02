#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


VERSION = "20260802-1"


UNIFIED_JS = r'''(() => {
  "use strict";

  if (window.NoorBrainUnifiedUI?.installed) return;

  const featureMap = [
    {key: "ai", label: "AI & Routines", icon: "✦", ids: ["nbMobileAiCenterV8", "nbAiControlCenterV8"]},
    {key: "voice", label: "HALO Voice", icon: "◉", ids: ["nbVoicePlatformV9"]},
    {key: "home", label: "Home Devices", icon: "⌂", ids: ["nbWholeHomeV10"]},
    {key: "family", label: "Family", icon: "●", ids: ["nbFamilyV11"]},
    {key: "islamic", label: "Islamic", icon: "☾", ids: ["nbIslamicV12"]},
    {key: "plugins", label: "Plugins", icon: "◇", ids: ["nbPluginsV13"]},
    {key: "system", label: "System Health", icon: "✓", ids: ["nbReleaseV14"]},
  ];

  let collecting = false;
  let observerTimer = 0;

  function isMobilePage() {
    return location.pathname.startsWith("/mobile") || matchMedia("(max-width: 760px)").matches;
  }

  function ensureHub() {
    let hub = document.getElementById("nbUnifiedHub");
    if (hub) return hub;

    const host =
      document.querySelector(".mobile-main") ||
      document.querySelector("main") ||
      document.querySelector("#app") ||
      document.body;

    hub = document.createElement("section");
    hub.id = "nbUnifiedHub";
    hub.className = "nb-unified-hub";
    hub.innerHTML = `
      <div class="nb-uh-head">
        <div>
          <small>NOORBRAIN</small>
          <h2>Features</h2>
          <p>Everything in one clean place</p>
        </div>
        <button id="nbUhClose" type="button" hidden>Close</button>
      </div>
      <div id="nbUhMenu" class="nb-uh-menu"></div>
      <div id="nbUhStage" class="nb-uh-stage" hidden></div>
    `;

    const first = host.querySelector("section, .mobile-card, .card");
    if (first) first.insertAdjacentElement("beforebegin", hub);
    else host.appendChild(hub);

    const menu = hub.querySelector("#nbUhMenu");
    menu.innerHTML = featureMap.map(feature => `
      <button type="button" data-nb-feature="${feature.key}">
        <i>${feature.icon}</i>
        <span>${feature.label}</span>
        <b>›</b>
      </button>
    `).join("");

    menu.querySelectorAll("[data-nb-feature]").forEach(button => {
      button.addEventListener("click", () => openFeature(button.dataset.nbFeature));
    });
    hub.querySelector("#nbUhClose").addEventListener("click", closeFeature);
    return hub;
  }

  function choosePanel(feature) {
    const candidates = feature.ids
      .map(id => document.getElementById(id))
      .filter(Boolean);

    if (feature.key === "ai" && candidates.length > 1) {
      const preferredId = isMobilePage() ? "nbMobileAiCenterV8" : "nbAiControlCenterV8";
      const preferred = document.getElementById(preferredId);
      candidates.filter(item => item !== preferred).forEach(item => {
        item.classList.add("nb-unified-duplicate");
        item.hidden = true;
      });
      return preferred || candidates[0];
    }
    return candidates[0] || null;
  }

  function collectFeatures() {
    if (collecting) return;
    collecting = true;
    try {
      const hub = ensureHub();
      const stage = hub.querySelector("#nbUhStage");
      for (const feature of featureMap) {
        const panel = choosePanel(feature);
        const button = hub.querySelector(`[data-nb-feature="${feature.key}"]`);
        if (!panel) {
          button?.classList.add("is-unavailable");
          continue;
        }
        button?.classList.remove("is-unavailable");
        panel.dataset.nbUnifiedFeature = feature.key;
        panel.classList.add("nb-unified-panel");
        panel.hidden = hub.dataset.openFeature !== feature.key;
        if (panel.parentElement !== stage) stage.appendChild(panel);
      }

      const pluginTest = document.querySelector("#nbPluginsV13 #nbP13Add");
      if (pluginTest) pluginTest.hidden = true;

      const releaseHeading = document.querySelector("#nbReleaseV14 h2");
      if (releaseHeading) releaseHeading.textContent = "System Health";
      const releaseEyebrow = document.querySelector("#nbReleaseV14 small");
      if (releaseEyebrow) releaseEyebrow.textContent = "SYSTEM";

      const startup = document.getElementById("nbVpStartup");
      if (startup) {
        startup.checked = false;
        startup.disabled = true;
        startup.closest("label")?.classList.add("nb-electronic-voice-disabled");
      }
    } finally {
      collecting = false;
    }
  }

  function openFeature(key) {
    collectFeatures();
    const hub = ensureHub();
    const stage = hub.querySelector("#nbUhStage");
    const menu = hub.querySelector("#nbUhMenu");
    const close = hub.querySelector("#nbUhClose");
    const panel = stage.querySelector(`[data-nb-unified-feature="${key}"]`);
    if (!panel) return;

    stage.querySelectorAll(".nb-unified-panel").forEach(item => item.hidden = true);
    panel.hidden = false;
    stage.hidden = false;
    menu.hidden = true;
    close.hidden = false;
    hub.dataset.openFeature = key;
    hub.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function closeFeature() {
    const hub = ensureHub();
    hub.querySelector("#nbUhStage").hidden = true;
    hub.querySelector("#nbUhMenu").hidden = false;
    hub.querySelector("#nbUhClose").hidden = true;
    delete hub.dataset.openFeature;
  }

  function muteElectronicVoice() {
    const synth = window.speechSynthesis;
    if (!synth) return;
    try { synth.cancel(); } catch (_) {}

    const mutedSpeak = function () {
      try { synth.cancel(); } catch (_) {}
      window.dispatchEvent(new CustomEvent("noorbrain:electronic-voice-blocked"));
    };
    mutedSpeak.__noorbrainElectronicVoiceOff = true;

    try {
      if (!synth.speak?.__noorbrainElectronicVoiceOff) {
        Object.defineProperty(synth, "speak", {
          configurable: true,
          writable: true,
          value: mutedSpeak,
        });
      }
    } catch (_) {
      try { synth.speak = mutedSpeak; } catch (_) {}
    }
  }

  function start() {
    document.body.classList.add("nb-unified-ui-active");
    muteElectronicVoice();
    collectFeatures();

    const observer = new MutationObserver(() => {
      clearTimeout(observerTimer);
      observerTimer = window.setTimeout(collectFeatures, 100);
    });
    observer.observe(document.body, {childList: true, subtree: true});

    window.setTimeout(() => {
      muteElectronicVoice();
      collectFeatures();
    }, 500);
    window.setTimeout(() => {
      muteElectronicVoice();
      collectFeatures();
    }, 1800);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }

  window.NoorBrainUnifiedUI = Object.freeze({
    installed: true,
    version: "1.0.0",
    open: openFeature,
    close: closeFeature,
    refresh: collectFeatures,
    electronicVoice: "disabled",
  });
})();
'''


UNIFIED_CSS = r'''.nb-unified-hub {
  width: min(100%, 900px);
  margin: 18px auto;
  padding: 20px;
  border: 1px solid #2c3d59;
  border-radius: 22px;
  color: #f6f9ff;
  background: linear-gradient(145deg, #151f31, #101827);
}

.nb-uh-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.nb-uh-head small {
  color: #61adff;
  font-weight: 850;
  letter-spacing: .13em;
}

.nb-uh-head h2 { margin: 3px 0; font-size: 24px; }
.nb-uh-head p { margin: 0; color: #9dabc2; }

.nb-uh-head button {
  padding: 10px 14px;
  border: 0;
  border-radius: 12px;
  color: #fff;
  background: #2b3c59;
  font-weight: 750;
}

.nb-uh-menu {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.nb-uh-menu button {
  display: grid;
  min-height: 84px;
  padding: 14px;
  border: 1px solid #2c405f;
  border-radius: 16px;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 11px;
  color: #f6f9ff;
  text-align: left;
  background: #1b2940;
}

.nb-uh-menu button i {
  display: grid;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  place-items: center;
  color: #89c8ff;
  background: #293c5d;
  font-style: normal;
  font-size: 18px;
}

.nb-uh-menu button b { color: #8091ab; font-size: 22px; }
.nb-uh-menu button.is-unavailable { display: none; }
.nb-uh-stage { margin-top: 4px; }

.nb-uh-stage > .nb-unified-panel {
  width: 100% !important;
  margin: 0 !important;
  box-shadow: none !important;
}

.nb-unified-duplicate,
.nb-electronic-voice-disabled {
  display: none !important;
}

#nbPluginsV13 #nbP13Add { display: none !important; }

@media (max-width: 720px) {
  .nb-unified-hub { padding: 16px; border-radius: 19px; }
  .nb-uh-menu { grid-template-columns: 1fr 1fr; gap: 8px; }
  .nb-uh-menu button { min-height: 74px; padding: 11px; }
}

@media (max-width: 390px) {
  .nb-uh-menu { grid-template-columns: 1fr; }
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


script = get("/dashboard-static/js/unified-product-ui.js?v=20260802-1")
assert "NoorBrainUnifiedUI" in script
assert "muteElectronicVoice" in script
assert "electronicVoice: \"disabled\"" in script
assert "nbPluginsV13" in script
assert "nbReleaseV14" in script
assert "nbWholeHomeV10" in script
assert "nbIslamicV12" in script

style = get("/dashboard-static/css/unified-product-ui.css?v=20260802-1")
assert ".nb-unified-hub" in style

for page in ("/studio", "/mobile"):
    html = get(page)
    assert "unified-product-ui.js?v=20260802-1" in html
    assert "unified-product-ui.css?v=20260802-1" in html

worker = get("/dashboard-pwa/sw.js")
assert "noorbrain-unified-product-ui-v1" in worker

config = get("/api/voice-platform-v9/config")
voice = json.loads(config)["config"]
assert voice["settings"]["startup_speech"] is False

print("ALL UNIFIED MOBILE WEB UI AND ELECTRONIC VOICE OFF TESTS PASSED")
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


def disable_startup_voice(path: Path) -> None:
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    data.setdefault("settings", {})["startup_speech"] = False
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def patch_worker(path: Path) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    content = re.sub(
        r'const CACHE\s*=\s*["\'][^"\']+["\'];',
        'const CACHE = "noorbrain-unified-product-ui-v1";',
        content,
        count=1,
    )
    assets = [
        "/dashboard-static/js/unified-product-ui.js?v=20260802-1",
        "/dashboard-static/css/unified-product-ui.css?v=20260802-1",
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
    voice_config = project / "data" / "voice_platform_v9.json"
    required = [studio, mobile, worker]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Required UI files missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"unified-product-ui-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    for source in required:
        relative = source.relative_to(project)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    if voice_config.is_file():
        target = backup / "data" / "voice_platform_v9.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(voice_config, target)

    js_path = project / "dashboard" / "js" / "unified-product-ui.js"
    css_path = project / "dashboard" / "css" / "unified-product-ui.css"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(UNIFIED_JS, encoding="utf-8")
    css_path.write_text(UNIFIED_CSS, encoding="utf-8")

    for page in (studio, mobile):
        inject(
            page,
            "</head>",
            f'<link rel="stylesheet" href="/dashboard-static/css/unified-product-ui.css?v={VERSION}">',
            r'\s*<link[^>]+unified-product-ui\.css[^>]*>',
        )
        inject(
            page,
            "</body>",
            f'<script src="/dashboard-static/js/unified-product-ui.js?v={VERSION}"></script>',
            r'\s*<script[^>]+unified-product-ui\.js[^>]*></script>',
        )

    disable_startup_voice(voice_config)
    patch_worker(worker)

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    smoke = tests / "unified_product_ui_smoke_test.py"
    smoke.write_text(SMOKE_TEST, encoding="utf-8")

    installer = project / "installer" / "unified_product_ui"
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
        "voice_backup = backup / 'data/voice_platform_v9.json'\n"
        "if voice_backup.is_file():\n"
        "    shutil.copy2(voice_backup, project / 'data/voice_platform_v9.json')\n"
        "(project / 'dashboard/js/unified-product-ui.js').unlink(missing_ok=True)\n"
        "(project / 'dashboard/css/unified-product-ui.css').unlink(missing_ok=True)\n"
        "print('UNIFIED PRODUCT UI ROLLBACK COMPLETE')\n",
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
    print("UNIFIED MOBILE + WEB PRODUCT UI INSTALLED")
    print("BACKEND FEATURES MOVED INTO FEATURES HUB")
    print("ELECTRONIC BROWSER VOICE DISABLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
