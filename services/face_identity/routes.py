from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .models import (
    EmbeddingEnroll,
    ImageEnroll,
    ImageRecognitionRequest,
    PersonCreate,
    RecognitionRequest,
)
from .service import face_identity_service
from .store import face_identity_store

router = APIRouter(
    prefix="/api/face-identity",
    tags=["Face Identity"],
)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "face_identity",
        "version": "3.7-d1.4",
        **face_identity_store.summary(),
    }


@router.post("/persons")
async def create_person(
    payload: PersonCreate,
) -> dict[str, Any]:
    person = await asyncio.to_thread(
        face_identity_store.create_person,
        payload.model_dump(mode="json"),
    )
    return {
        "status": "created",
        "person": person,
    }


@router.get("/persons")
async def persons() -> dict[str, Any]:
    items = await asyncio.to_thread(
        face_identity_store.list_persons
    )
    return {
        "status": "ok",
        "count": len(items),
        "persons": items,
    }


@router.delete("/persons/{person_id}")
async def delete_person(person_id: str) -> dict[str, Any]:
    removed = await asyncio.to_thread(
        face_identity_store.delete_person,
        person_id,
    )

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Person not found.",
        )

    return {
        "status": "deleted",
        "person_id": person_id,
    }


@router.post("/enroll/embedding")
async def enroll_embedding(
    payload: EmbeddingEnroll,
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            face_identity_service.enroll_embedding,
            person_id=payload.person_id,
            embedding=payload.embedding,
            source=payload.source,
            metadata=payload.metadata,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.post("/enroll/image")
async def enroll_image(
    payload: ImageEnroll,
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            face_identity_service.enroll_image,
            person_id=payload.person_id,
            image_base64=payload.image_base64,
            source=payload.source,
            metadata=payload.metadata,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post("/recognize/embedding")
async def recognize_embedding(
    payload: RecognitionRequest,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        face_identity_service.recognize,
        embedding=payload.embedding,
        threshold=payload.threshold,
        zone=payload.zone,
        track_id=payload.track_id,
        metadata=payload.metadata,
    )


@router.post("/recognize/image")
async def recognize_image(
    payload: ImageRecognitionRequest,
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            face_identity_service.recognize_image,
            image_base64=payload.image_base64,
            threshold=payload.threshold,
            zone=payload.zone,
            track_id=payload.track_id,
            metadata=payload.metadata,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get("/events")
async def events(
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    items = await asyncio.to_thread(
        face_identity_store.list_events,
        limit,
    )
    return {
        "status": "ok",
        "count": len(items),
        "events": items,
    }


@router.get("/summary")
async def summary() -> dict[str, Any]:
    return await asyncio.to_thread(
        face_identity_store.summary
    )
