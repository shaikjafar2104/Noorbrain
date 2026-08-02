from __future__ import annotations

from pathlib import Path
import subprocess

PROJECT = Path.home() / "Projects" / "NoorBrain"
SERVICE = PROJECT / "services" / "halo_decision_v8"
JS = PROJECT / "dashboard" / "js" / "sprint8a1-decision-engine.js"
CSS = PROJECT / "dashboard" / "css" / "sprint8a1-decision-engine.css"

required = [SERVICE / "routes.py", JS, CSS, PROJECT / "main.py"]
missing = [str(path) for path in required if not path.exists()]

if missing:
    raise SystemExit(
        "Sprint 8A.1 files are missing:\n" + "\n".join(missing)
    )

subprocess.run(
    [
        str(PROJECT / "venv" / "bin" / "python"),
        "-m",
        "py_compile",
        str(PROJECT / "main.py"),
    ],
    check=True,
)

print("Sprint 8A.1 already installed and verified.")
