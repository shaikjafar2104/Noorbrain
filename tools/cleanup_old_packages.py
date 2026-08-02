from __future__ import annotations

from pathlib import Path
import shutil

downloads = Path.home() / "Downloads"

patterns = [
    "NoorBrain_Sprint_*.zip",
    "NoorBrain_Sprint_*",
]

removed = []

for pattern in patterns:
    for path in downloads.glob(pattern):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

        removed.append(str(path))

print(f"Removed {len(removed)} old Sprint packages.")
for item in removed:
    print(item)
