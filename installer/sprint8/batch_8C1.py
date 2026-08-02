#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


VERSION = "8.3.0"
ASSET_VERSION = "20260731-1"
SCRIPT_NAME = "sprint8c-voice-repeat-guard.js"


VOICE_GUARD_JS = r'''(() => {
  "use strict";

  if (window.NoorBrainVoiceRepeatGuard?.installed) return;

  const state = {
    installed: true,
    version: "8.3.0",
    lastText: "",
    lastAt: 0,
    speakingText: "",
    speaking: false,
    lastActionAt: 0,
    blocked: 0,
  };

  const SAME_REPLY_WINDOW_MS = 12000;
  const ACTION_WINDOW_MS = 1200;
  const STORAGE_KEY = "noorbrain.voice.last-spoken.v1";

  function normalize(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function readShared() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch (_) {
      return {};
    }
  }

  function writeShared(text, at) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({text, at}));
    } catch (_) {}
  }

  function recentlySpoken(text, now = Date.now()) {
    const normalized = normalize(text);
    if (!normalized) return true;

    if (
      normalized === state.speakingText ||
      (normalized === state.lastText && now - state.lastAt < SAME_REPLY_WINDOW_MS)
    ) {
      return true;
    }

    const shared = readShared();
    return (
      normalize(shared.text) === normalized &&
      now - Number(shared.at || 0) < SAME_REPLY_WINDOW_MS
    );
  }

  function installSpeechGuard() {
    const synth = window.speechSynthesis;
    if (!synth || typeof synth.speak !== "function") return false;
    if (synth.speak.__noorbrainGuarded) return true;

    const nativeSpeak = synth.speak.bind(synth);
    const guardedSpeak = function (utterance) {
      const text = normalize(utterance?.text);
      const now = Date.now();

      if (recentlySpoken(text, now)) {
        state.blocked += 1;
        window.dispatchEvent(new CustomEvent("noorbrain:voice-duplicate-blocked", {
          detail: {text, blocked: state.blocked},
        }));
        return;
      }

      state.lastText = text;
      state.lastAt = now;
      state.speakingText = text;
      state.speaking = true;
      writeShared(text, now);

      const finish = () => {
        if (state.speakingText === text) {
          state.speakingText = "";
          state.speaking = false;
        }
      };

      utterance.addEventListener?.("end", finish, {once: true});
      utterance.addEventListener?.("error", finish, {once: true});
      nativeSpeak(utterance);
    };

    guardedSpeak.__noorbrainGuarded = true;
    synth.speak = guardedSpeak;
    return true;
  }

  function isVoiceAction(target) {
    const button = target?.closest?.("button, [role='button']");
    if (!button) return false;

    const identity = [
      button.id,
      button.className,
      button.getAttribute("aria-label"),
      button.textContent,
    ].join(" ").toLowerCase();

    return /talk to halo|ask halo|send|push.to.talk|microphone|\bmic\b|voice/.test(identity);
  }

  document.addEventListener("click", event => {
    if (!isVoiceAction(event.target)) return;

    const now = Date.now();
    if (now - state.lastActionAt < ACTION_WINDOW_MS) {
      event.preventDefault();
      event.stopImmediatePropagation();
      state.blocked += 1;
      return;
    }
    state.lastActionAt = now;
  }, true);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && window.speechSynthesis?.speaking) {
      window.speechSynthesis.cancel();
      state.speaking = false;
      state.speakingText = "";
    }
  });

  window.addEventListener("pagehide", () => {
    window.speechSynthesis?.cancel();
  });

  installSpeechGuard();
  setTimeout(installSpeechGuard, 500);
  setTimeout(installSpeechGuard, 2000);

  window.NoorBrainVoiceRepeatGuard = Object.freeze({
    installed: true,
    version: state.version,
    status: () => ({...state}),
    reset: () => {
      state.lastText = "";
      state.lastAt = 0;
      state.speakingText = "";
      state.speaking = false;
      try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
      window.speechSynthesis?.cancel();
    },
  });
})();
'''


SMOKE_TEST = r'''from __future__ import annotations

import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> str:
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        assert response.status == 200
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    script = get(
        "/dashboard-static/js/"
        "sprint8c-voice-repeat-guard.js?v=20260731-1"
    )
    assert "NoorBrainVoiceRepeatGuard" in script
    assert "SAME_REPLY_WINDOW_MS = 12000" in script
    assert "noorbrain:voice-duplicate-blocked" in script

    mobile = get("/mobile")
    assert "sprint8c-voice-repeat-guard.js?v=20260731-1" in mobile

    studio = get("/studio")
    assert "sprint8c-voice-repeat-guard.js?v=20260731-1" in studio

    sw = get("/dashboard-pwa/sw.js")
    assert "noorbrain-sprint8c-voice-stability-v1" in sw

    print("ALL SPRINT 8C VOICE STABILITY TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


ROLLBACK = r'''from __future__ import annotations

import json
import shutil
from pathlib import Path


def find_project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "dashboard").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


project = find_project()
manifest_path = project / "installer" / "sprint8" / ".sprint8c_voice_backup.json"
if not manifest_path.is_file():
    raise SystemExit("Sprint 8C backup manifest not found.")

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
backup = Path(manifest["backup"])

for relative in manifest["files"]:
    source = backup / relative
    target = project / relative
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

(project / "dashboard" / "js" / "sprint8c-voice-repeat-guard.js").unlink(missing_ok=True)
print("SPRINT 8C VOICE STABILITY ROLLBACK COMPLETE")
'''


def find_project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "dashboard").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


def inject_asset(html_path: Path, asset: str) -> None:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r'\s*<script[^>]+sprint8c-voice-repeat-guard\.js[^>]*></script>',
        "",
        text,
        flags=re.IGNORECASE,
    )
    position = text.lower().rfind("</body>")
    if position < 0:
        raise RuntimeError(f"Missing </body> in {html_path}")
    text = text[:position] + "  " + asset + "\n" + text[position:]
    html_path.write_text(text, encoding="utf-8")


def patch_service_worker(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r'const CACHE\s*=\s*["\'][^"\']+["\'];',
        'const CACHE = "noorbrain-sprint8c-voice-stability-v1";',
        text,
        count=1,
    )
    asset = f'/dashboard-static/js/{SCRIPT_NAME}?v={ASSET_VERSION}'
    if asset not in text:
        match = re.search(r"const SHELL\s*=\s*\[", text)
        if match:
            text = text[:match.end()] + f'\n  "{asset}",' + text[match.end():]
        else:
            text += (
                "\nself.addEventListener(\"install\", event => {\n"
                "  event.waitUntil(caches.open(\"noorbrain-sprint8c-voice-stability-v1\")\n"
                f"    .then(cache => cache.add(\"{asset}\")));\n"
                "});\n"
            )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    project = find_project()
    dashboard = project / "dashboard"
    mobile_html = dashboard / "mobile" / "index.html"
    studio_html = dashboard / "index.html"
    sw_path = dashboard / "pwa" / "sw.js"

    required = [mobile_html, studio_html, sw_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Required files missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint8c-voice-stability-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)

    backed_up = []
    for source in required:
        relative = source.relative_to(project)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        backed_up.append(str(relative))

    js_path = dashboard / "js" / SCRIPT_NAME
    js_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.write_text(VOICE_GUARD_JS, encoding="utf-8")

    asset = (
        '<script src="/dashboard-static/js/'
        f'{SCRIPT_NAME}?v={ASSET_VERSION}"></script>'
    )
    inject_asset(mobile_html, asset)
    inject_asset(studio_html, asset)
    patch_service_worker(sw_path)

    installer_dir = project / "installer" / "sprint8"
    installer_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": VERSION,
        "backup": str(backup),
        "files": backed_up,
    }
    (installer_dir / ".sprint8c_voice_backup.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (installer_dir / "rollback_8C1.py").write_text(ROLLBACK, encoding="utf-8")

    tests_dir = project / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    smoke_path = tests_dir / "sprint8c_voice_smoke_test.py"
    smoke_path.write_text(SMOKE_TEST, encoding="utf-8")

    subprocess.run(
        [
            str(project / "venv" / "bin" / "python"),
            "-m",
            "py_compile",
            str(Path(__file__).resolve()),
            str(installer_dir / "rollback_8C1.py"),
            str(smoke_path),
        ],
        check=True,
    )

    print("SPRINT 8C.1 HALO VOICE REPEAT FIX INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
