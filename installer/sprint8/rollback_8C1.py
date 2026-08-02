from __future__ import annotations

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
