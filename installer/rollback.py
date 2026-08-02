from __future__ import annotations

from pathlib import Path
import shutil
from common import PROJECT, load_state

state = load_state()
backups = state.get("backups", [])

if not backups:
    raise SystemExit("No installer backups found.")

latest = Path(backups[-1]["path"])

if not latest.exists():
    raise SystemExit(f"Backup missing: {latest}")

for item in latest.iterdir():
    target = PROJECT / item.name

    if item.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(item, target)
    else:
        shutil.copy2(item, target)

print("Rollback complete:", latest)
