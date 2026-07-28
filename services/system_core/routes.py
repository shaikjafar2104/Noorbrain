"""Sprint 8.5 Milestone 1 system API routes."""
from fastapi import APIRouter, HTTPException

from .migrations import migration_manager
from .validation import startup_validator
from .version import build_info

router = APIRouter(prefix="/api/system", tags=["System Core"])


@router.get("/health")
def system_core_health():
    validation = startup_validator.run()
    return {
        "status": "healthy" if validation["failed"] == 0 else "degraded",
        "component": "system-core",
        "validation": {
            "passed": validation["passed"],
            "warnings": validation["warnings"],
            "failed": validation["failed"],
        },
    }


@router.get("/version")
def system_version():
    info = build_info()
    info["database_schema"] = migration_manager.current_version()
    return info


@router.get("/validation")
def validation_report():
    return startup_validator.run()


@router.get("/migrations")
def migration_status():
    return {
        "status": "ok",
        "current_version": migration_manager.current_version(),
        "history": migration_manager.history(),
    }


@router.post("/migrations/apply")
def apply_migrations():
    try:
        return migration_manager.apply_pending()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Migration failed: {exc}") from exc
