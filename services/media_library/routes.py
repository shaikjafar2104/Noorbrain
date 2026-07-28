from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services.media_library.media_manager import (
    InvalidMediaError,
    MediaLibraryError,
    MediaNotFoundError,
    media_library,
)


router = APIRouter(
    prefix="/media",
    tags=["Media Library"],
)

api_router = APIRouter(
    prefix="/api/media",
    tags=["Media Library"],
)


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)


def _error_response(error: Exception) -> HTTPException:
    if isinstance(error, MediaNotFoundError):
        return HTTPException(status_code=404, detail=str(error))

    if isinstance(error, InvalidMediaError):
        return HTTPException(status_code=400, detail=str(error))

    return HTTPException(status_code=500, detail=str(error))


def _list_media(
    category: str | None,
    search: str | None,
) -> dict:
    return {
        "status": "ok",
        "items": media_library.list_items(
            category=category,
            search=search,
        ),
        "categories": media_library.list_categories(),
    }


def _get_media(media_id: str) -> dict:
    try:
        return {
            "status": "ok",
            "item": media_library.get_item(media_id),
        }
    except MediaLibraryError as error:
        raise _error_response(error) from error


async def _upload_media(
    file: UploadFile,
    category: str,
    name: str | None,
) -> dict:
    try:
        item = media_library.save_upload(
            file_stream=file.file,
            original_filename=file.filename or "audio",
            category=category,
            display_name=name,
        )

        return {
            "status": "created",
            "message": "Audio uploaded successfully.",
            "item": item,
        }

    except MediaLibraryError as error:
        raise _error_response(error) from error

    finally:
        await file.close()


def _delete_media(media_id: str) -> dict:
    try:
        item = media_library.delete_item(media_id)

        return {
            "status": "deleted",
            "message": "Audio deleted successfully.",
            "item": item,
        }

    except MediaLibraryError as error:
        raise _error_response(error) from error


def _play_media(media_id: str) -> dict:
    try:
        return media_library.play_item(media_id)

    except MediaLibraryError as error:
        raise _error_response(error) from error


def _media_file(media_id: str) -> FileResponse:
    try:
        item = media_library.get_item(media_id)
        file_path = media_library.get_file_path(media_id)

        return FileResponse(
            path=file_path,
            media_type=item.get("mime_type"),
            filename=item.get("original_filename"),
            content_disposition_type="inline",
        )

    except MediaLibraryError as error:
        raise _error_response(error) from error


@router.get("")
@api_router.get("")
def list_media(
    category: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> dict:
    return _list_media(category, search)


@router.get("/status")
@api_router.get("/status")
def media_status() -> dict:
    return media_library.status()


@router.get("/categories")
@api_router.get("/categories")
def list_categories() -> dict:
    return {
        "status": "ok",
        "categories": media_library.list_categories(),
    }


@router.post("/categories")
@api_router.post("/categories")
def create_category(payload: CategoryCreateRequest) -> dict:
    category = media_library.create_category(payload.name)

    return {
        "status": "created",
        "message": "Category created successfully.",
        "category": category,
    }


@router.get("/{media_id}")
@api_router.get("/{media_id}")
def get_media(media_id: str) -> dict:
    return _get_media(media_id)


@router.post("/upload", status_code=201)
@api_router.post("/upload", status_code=201)
async def upload_media(
    file: Annotated[UploadFile, File(...)],
    category: Annotated[str, Form()] = "custom",
    name: Annotated[str | None, Form()] = None,
) -> dict:
    return await _upload_media(file, category, name)


@router.get("/{media_id}/file")
@api_router.get("/{media_id}/file")
def media_file(media_id: str) -> FileResponse:
    return _media_file(media_id)


@router.post("/{media_id}/play")
@api_router.post("/{media_id}/play")
def play_media(media_id: str) -> dict:
    return _play_media(media_id)


@router.post("/play/{media_id}")
@api_router.post("/play/{media_id}")
def play_media_legacy(media_id: str) -> dict:
    return _play_media(media_id)


@router.post("/stop")
@api_router.post("/stop")
def stop_media() -> dict:
    return media_library.stop_playback()


@router.delete("/{media_id}")
@api_router.delete("/{media_id}")
def delete_media(media_id: str) -> dict:
    return _delete_media(media_id)
