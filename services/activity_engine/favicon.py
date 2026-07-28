from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["Favicon"])


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(
        content=b"",
        media_type="image/x-icon",
        status_code=204,
        headers={"Cache-Control": "public, max-age=86400"},
    )
