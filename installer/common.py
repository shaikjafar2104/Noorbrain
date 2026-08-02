from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import shutil

PROJECT = Path.home() / "Projects" / "NoorBrain"
INSTALLER = PROJECT / "installer"
STATE = INSTALLER / "state.json"


def load_state() -> dict:
    if not STATE.exists():
        return {"installed": [], "backups": []}

    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"installed": [], "backups": []}


def save_state(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def backup(name: str, paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = PROJECT / "backups" / f"{name}-{stamp}"
    target.mkdir(parents=True, exist_ok=True)

    for source in paths:
        if not source.exists():
            continue

        destination = target / source.name

        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

    state = load_state()
    state.setdefault("backups", []).append({
        "name": name,
        "path": str(target),
        "created": stamp,
    })
    save_state(state)

    return target


def mark_installed(batch: str) -> None:
    state = load_state()
    installed = state.setdefault("installed", [])

    if batch not in installed:
        installed.append(batch)

    save_state(state)
