from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["Activity Dashboard Assets"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTIVITY_JS = PROJECT_ROOT / "dashboard" / "js" / "activity.js"


@router.get("/dashboard/js/activity.js")
def activity_javascript() -> FileResponse:
    if not ACTIVITY_JS.is_file():
        raise HTTPException(
            status_code=404,
            detail="activity.js not found",
        )

    return FileResponse(
        ACTIVITY_JS,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )
