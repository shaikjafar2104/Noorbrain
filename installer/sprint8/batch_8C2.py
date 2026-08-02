#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path


BOOT_STATE = '''    userActivated: false,
    bootMuteUntil: Date.now() + 8000,
'''

BOOT_GUARD = '''      if (!state.userActivated && now < state.bootMuteUntil) {
        state.blocked += 1;
        window.speechSynthesis?.cancel();
        return;
      }

'''

ACTIVATION_GUARD = '''
  function activateVoiceFromUser(event) {
    if (event?.isTrusted === false) return;
    state.userActivated = true;
    state.bootMuteUntil = 0;
  }

  for (const eventName of ["pointerdown", "touchstart", "keydown"]) {
    document.addEventListener(eventName, activateVoiceFromUser, {
      capture: true,
      passive: true,
      once: true,
    });
  }

  function cancelStartupVoice() {
    if (!state.userActivated && Date.now() < state.bootMuteUntil) {
      window.speechSynthesis?.cancel();
    }
  }

  cancelStartupVoice();
  setTimeout(cancelStartupVoice, 100);
  setTimeout(cancelStartupVoice, 500);
  setTimeout(cancelStartupVoice, 1500);
'''


SMOKE_TEST = '''from __future__ import annotations

import urllib.request


URL = (
    "http://127.0.0.1:8001/dashboard-static/js/"
    "sprint8c-voice-repeat-guard.js?v=20260801-2"
)


with urllib.request.urlopen(URL, timeout=30) as response:
    script = response.read().decode("utf-8", errors="replace")

assert "bootMuteUntil: Date.now() + 8000" in script
assert "userActivated: false" in script
assert "cancelStartupVoice" in script
assert "activateVoiceFromUser" in script
assert "event?.isTrusted === false" in script

print("ALL SPRINT 8C.2 STARTUP VOICE SILENCE TESTS PASSED")
'''


def find_project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "dashboard").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


def replace_version(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace(
        "sprint8c-voice-repeat-guard.js?v=20260731-1",
        "sprint8c-voice-repeat-guard.js?v=20260801-2",
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    project = find_project()
    script = (
        project / "dashboard" / "js" /
        "sprint8c-voice-repeat-guard.js"
    )
    mobile = project / "dashboard" / "mobile" / "index.html"
    studio = project / "dashboard" / "index.html"
    worker = project / "dashboard" / "pwa" / "sw.js"

    required = [script, mobile, studio, worker]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(
            "Install Sprint 8C.1 first. Missing:\n" + "\n".join(missing)
        )

    text = script.read_text(encoding="utf-8", errors="replace")
    if "NoorBrainVoiceRepeatGuard" not in text:
        raise SystemExit("Sprint 8C.1 voice guard is invalid.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint8c2-startup-silence-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)

    for source in required:
        relative = source.relative_to(project)
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    if "bootMuteUntil: Date.now() + 8000" not in text:
        anchor = "    blocked: 0,\n"
        if anchor not in text:
            raise SystemExit("Voice guard state anchor not found.")
        text = text.replace(anchor, anchor + BOOT_STATE, 1)

    if "if (!state.userActivated && now < state.bootMuteUntil)" not in text:
        anchor = "      const now = Date.now();\n\n"
        if anchor not in text:
            raise SystemExit("Voice speak anchor not found.")
        text = text.replace(anchor, anchor + BOOT_GUARD, 1)

    if "function activateVoiceFromUser(event)" not in text:
        anchor = "  installSpeechGuard();\n"
        if anchor not in text:
            raise SystemExit("Voice install anchor not found.")
        text = text.replace(anchor, ACTIVATION_GUARD + "\n" + anchor, 1)

    script.write_text(text, encoding="utf-8")

    for path in (mobile, studio, worker):
        replace_version(path)

    worker_text = worker.read_text(encoding="utf-8", errors="replace")
    worker_text = worker_text.replace(
        "noorbrain-sprint8c-voice-stability-v1",
        "noorbrain-sprint8c2-startup-silence-v1",
    )
    worker.write_text(worker_text, encoding="utf-8")

    test_path = project / "tests" / "sprint8c2_startup_voice_smoke_test.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(SMOKE_TEST, encoding="utf-8")

    rollback_path = project / "installer" / "sprint8" / "rollback_8C2.py"
    rollback_path.write_text(
        "from pathlib import Path\n"
        "import shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "for relative in [\n"
        "    'dashboard/js/sprint8c-voice-repeat-guard.js',\n"
        "    'dashboard/mobile/index.html',\n"
        "    'dashboard/index.html',\n"
        "    'dashboard/pwa/sw.js',\n"
        "]:\n"
        "    source = backup / relative\n"
        "    target = project / relative\n"
        "    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    shutil.copy2(source, target)\n"
        "print('SPRINT 8C.2 ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            str(project / "venv" / "bin" / "python"),
            "-m", "py_compile",
            str(Path(__file__).resolve()),
            str(test_path),
            str(rollback_path),
        ],
        check=True,
    )

    print("SPRINT 8C.2 STARTUP VOICE SILENCE INSTALLED")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
