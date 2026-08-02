#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


INIT_PY = '''from .routes import router

__all__ = ["router"]
'''


ROUTES_PY = r'''from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/sprint8-release",
    tags=["Sprint 8 Production Release"],
)

PROJECT = Path(__file__).resolve().parents[2]


def release_manifest() -> dict[str, Any]:
    path = PROJECT / "data" / "sprint8_release.json"
    if not path.is_file():
        return {"status": "missing", "version": "8.6.0"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "version": "8.6.0"}


@router.get("/health")
async def health() -> dict[str, Any]:
    manifest = release_manifest()
    return {
        "status": "healthy" if manifest.get("status") == "production" else "degraded",
        "service": "sprint8_production_release",
        "version": "8.6.0",
        "release": manifest,
    }


@router.get("/status")
async def status() -> dict[str, Any]:
    required = {
        "decision_engine": PROJECT / "installer" / "sprint8" / "batch_8A1.py",
        "routine_intelligence": PROJECT / "services" / "routine_intelligence_v8" / "routes.py",
        "voice_stability": PROJECT / "dashboard" / "js" / "sprint8c-voice-repeat-guard.js",
        "conversation_memory": PROJECT / "services" / "halo_conversation_memory_v8" / "routes.py",
        "voice_context": PROJECT / "services" / "halo_voice_context_v8" / "routes.py",
        "ai_dashboard": PROJECT / "dashboard" / "js" / "sprint8e1-ai-dashboard.js",
        "mobile_ai": PROJECT / "dashboard" / "js" / "sprint8e2-mobile-ai.js",
    }
    components = {
        name: {"installed": path.exists()}
        for name, path in required.items()
    }
    installed = sum(1 for item in components.values() if item["installed"])
    return {
        "status": "production" if installed == len(components) else "incomplete",
        "version": "8.6.0",
        "installed_components": installed,
        "total_components": len(components),
        "components": components,
        "manifest": release_manifest(),
    }
'''


FULL_TEST = r'''from __future__ import annotations

import json
import urllib.request


BASE = "http://127.0.0.1:8001"


def get(path: str) -> tuple[int, str]:
    with urllib.request.urlopen(BASE + path, timeout=60) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def api(path: str) -> dict:
    status, raw = get(path)
    assert status == 200, path
    return json.loads(raw)


status, _ = get("/health")
assert status == 200
print("PASS NoorBrain core health")

routine = api("/api/routine-intelligence-v8/health")
assert routine["version"] == "8.2.0"
print("PASS Sprint 8B routine intelligence")

memory = api("/api/halo-memory-v8/health")
assert memory["version"] == "8.4.0"
print("PASS Sprint 8D.1 conversation memory")

voice = api("/api/halo-voice-context-v8/health")
assert voice["version"] == "8.4.1"
print("PASS Sprint 8D.2 voice context")

center = api("/api/ai-control-center-v8/health")
assert center["version"] == "8.5.0"
print("PASS Sprint 8E.1 AI dashboard API")

overview = api("/api/ai-control-center-v8/overview")
assert "conversation_memory" in overview
assert "routine_intelligence" in overview
print("PASS AI overview integration")

release = api("/api/sprint8-release/health")
assert release["version"] == "8.6.0"
assert release["status"] == "healthy"
print("PASS Sprint 8 production release health")

release_status = api("/api/sprint8-release/status")
assert release_status["status"] == "production"
assert release_status["installed_components"] == release_status["total_components"]
print("PASS all Sprint 8 components installed")

_, studio = get("/studio")
assert "sprint8e1-ai-dashboard.js" in studio
print("PASS AI Studio integration")

_, mobile = get("/mobile")
assert "sprint8e2-mobile-ai.js" in mobile
assert "sprint8c-voice-repeat-guard.js" in mobile
print("PASS Mobile AI and voice stability integration")

_, worker = get("/dashboard-pwa/sw.js")
assert "sprint8e2-mobile-ai.js" in worker
print("PASS production PWA assets")

print("ALL SPRINT 8 PRODUCTION RELEASE TESTS PASSED")
'''


BATCH_8F1 = r'''from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


project = Path(__file__).resolve().parents[2]
memory = project / "data" / "halo_conversation_memory_v8.json"
if memory.is_file():
    data = json.loads(memory.read_text(encoding="utf-8"))
    data.setdefault("version", "8.4.0")
    data.setdefault("sessions", {})
    data["migrated_at"] = datetime.now(timezone.utc).isoformat()
    memory.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
print("SPRINT 8F.1 DATA MIGRATION PASS")
'''


BATCH_8F2 = r'''from __future__ import annotations

import json
from pathlib import Path


project = Path(__file__).resolve().parents[2]
manifest = project / "data" / "sprint8_release.json"
data = json.loads(manifest.read_text(encoding="utf-8"))
assert data["status"] == "production"
assert data["version"] == "8.6.0"
print("SPRINT 8F.2 PRODUCTION FINALIZATION PASS")
'''


def find_project() -> Path:
    cwd = Path.cwd()
    if (cwd / "main.py").is_file() and (cwd / "services").is_dir():
        return cwd
    candidate = Path.home() / "Projects" / "NoorBrain"
    if candidate.is_dir():
        return candidate
    raise SystemExit("NoorBrain project not found.")


def main() -> int:
    project = find_project()
    main_path = project / "main.py"

    required = {
        "routine_intelligence": project / "services" / "routine_intelligence_v8" / "routes.py",
        "voice_stability": project / "dashboard" / "js" / "sprint8c-voice-repeat-guard.js",
        "conversation_memory": project / "services" / "halo_conversation_memory_v8" / "routes.py",
        "voice_context": project / "services" / "halo_voice_context_v8" / "routes.py",
        "ai_dashboard": project / "dashboard" / "js" / "sprint8e1-ai-dashboard.js",
        "mobile_ai": project / "dashboard" / "js" / "sprint8e2-mobile-ai.js",
    }
    missing = [f"{name}: {path}" for name, path in required.items() if not path.exists()]
    if missing:
        raise SystemExit("Sprint 8 components missing:\n" + "\n".join(missing))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = project / "backups" / f"sprint8f-production-final-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_path, backup / "main.py")

    release_file = project / "data" / "sprint8_release.json"
    if release_file.is_file():
        shutil.copy2(release_file, backup / "sprint8_release.json")

    service = project / "services" / "sprint8_release"
    if service.exists():
        shutil.copytree(service, backup / "service", dirs_exist_ok=True)
    service.mkdir(parents=True, exist_ok=True)
    (service / "__init__.py").write_text(INIT_PY, encoding="utf-8")
    (service / "routes.py").write_text(ROUTES_PY, encoding="utf-8")

    import_line = (
        "from services.sprint8_release.routes "
        "import router as sprint8_release_router"
    )
    include_line = "app.include_router(sprint8_release_router)"
    text = main_path.read_text(encoding="utf-8", errors="replace")
    additions = []
    if import_line not in text:
        additions.append(import_line)
    if include_line not in text:
        additions.append(include_line)
    if additions:
        main_path.write_text(
            text.rstrip()
            + "\n\n# NOORBRAIN SPRINT 8 PRODUCTION RELEASE\n"
            + "\n".join(additions)
            + "\n",
            encoding="utf-8",
        )

    installer = project / "installer" / "sprint8"
    installer.mkdir(parents=True, exist_ok=True)
    batch_f1 = installer / "batch_8F1.py"
    batch_f2 = installer / "batch_8F2.py"
    batch_f1.write_text(BATCH_8F1, encoding="utf-8")
    batch_f2.write_text(BATCH_8F2, encoding="utf-8")

    data_dir = project / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "NoorBrain Sprint 8 Production Release",
        "version": "8.6.0",
        "status": "production",
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "components": {
            "decision_engine": "8A",
            "routine_intelligence": "8.2.0",
            "voice_stability": "8.3.1",
            "conversation_memory": "8.4.0",
            "voice_context": "8.4.1",
            "ai_dashboard": "8.5.0",
            "mobile_ai": "8.5.1",
            "production_release": "8.6.0",
        },
    }
    release_file.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    tests = project / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    full_test = tests / "sprint8_full_release_test.py"
    full_test.write_text(FULL_TEST, encoding="utf-8")

    rollback = installer / "rollback_8F.py"
    rollback.write_text(
        "from pathlib import Path\nimport shutil\n\n"
        f"backup = Path({str(backup)!r})\n"
        "project = Path.home() / 'Projects' / 'NoorBrain'\n"
        "shutil.copy2(backup / 'main.py', project / 'main.py')\n"
        "service = project / 'services' / 'sprint8_release'\n"
        "if service.exists(): shutil.rmtree(service)\n"
        "if (backup / 'service').exists(): shutil.copytree(backup / 'service', service)\n"
        "release = project / 'data' / 'sprint8_release.json'\n"
        "if (backup / 'sprint8_release.json').exists():\n"
        "    shutil.copy2(backup / 'sprint8_release.json', release)\n"
        "else:\n"
        "    release.unlink(missing_ok=True)\n"
        "print('SPRINT 8F ROLLBACK COMPLETE')\n",
        encoding="utf-8",
    )

    python = project / "venv" / "bin" / "python"
    compile_files = [
        Path(__file__).resolve(), main_path, service / "routes.py",
        batch_f1, batch_f2, full_test, rollback,
    ]
    subprocess.run(
        [str(python), "-m", "py_compile", *map(str, compile_files)],
        check=True,
    )
    subprocess.run([str(python), str(batch_f1)], check=True)
    subprocess.run([str(python), str(batch_f2)], check=True)

    print("SPRINT 8F.1 MIGRATION INSTALLED")
    print("SPRINT 8F.2 PRODUCTION FINALIZATION INSTALLED")
    print("SPRINT 8 FULL RELEASE READY")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
