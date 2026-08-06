from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .unknown_gallery import unknown_face_gallery


router = APIRouter(prefix="/api/person-gallery", tags=["Person Gallery"])


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "person_gallery",
        "version": "16.0.0",
        "privacy": "local-only",
        "unknown_faces": len(unknown_face_gallery.list(200)),
    }


@router.get("/unknown")
def unknown(limit: int = Query(default=50, ge=1, le=200)):
    items = unknown_face_gallery.list(limit)
    return {"status": "ok", "count": len(items), "items": items}


@router.get("/unknown/{item_id}/image")
def image(item_id: str):
    path = unknown_face_gallery.image_path(item_id)
    if path is None:
        raise HTTPException(404, "Gallery image not found")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.delete("/unknown/{item_id}")
def delete(item_id: str):
    if not unknown_face_gallery.delete(item_id):
        raise HTTPException(404, "Gallery item not found")
    return {"status": "deleted", "id": item_id}
