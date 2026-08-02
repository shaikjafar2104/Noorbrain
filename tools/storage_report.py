from __future__ import annotations

from pathlib import Path
import shutil

project = Path.home() / "Projects" / "NoorBrain"


def size(path: Path) -> int:
    total = 0

    if not path.exists():
        return 0

    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            pass

    return total


def human(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)

    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024

    return f"{amount:.1f} TB"


disk = shutil.disk_usage(project)

print("NoorBrain storage report")
print("Project :", human(size(project)))
print("Backups :", human(size(project / "backups")))
print("Exports :", human(size(project / "exports")))
print("Models  :", human(size(project / "models")))
print("Free    :", human(disk.free))
