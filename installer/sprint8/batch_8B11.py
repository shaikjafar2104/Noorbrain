from pathlib import Path
import subprocess

P = Path.home() / "Projects" / "NoorBrain"

required = [
    P / "services" / "routine_intelligence_v8" / "routes.py",
    P / "dashboard" / "js" / "sprint8b-routine-intelligence.js",
    P / "dashboard" / "css" / "sprint8b-routine-intelligence.css",
    P / "main.py",
]

missing = [str(path) for path in required if not path.exists()]

if missing:
    raise SystemExit("Missing:\n" + "\n".join(missing))

subprocess.run(
    [
        str(P / "venv" / "bin" / "python"),
        "-m",
        "py_compile",
        str(P / "main.py"),
        str(P / "services" / "routine_intelligence_v8" / "routes.py"),
    ],
    check=True,
)

print("SPRINT 8B.11 INSTALLER PASS")
