from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from services.person_ai.face_enrollment import face_enrollment
from services.person_ai.identity_engine import identity_engine
from services.person_ai.person_engine import person_engine
from services.person_ai.person_registry import registry
from shared.frame_buffer import frame_buffer


router = APIRouter(tags=["Person AI"])


class PersonCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    category: Literal[
        "family",
        "friend",
        "guest",
        "staff",
        "child",
        "visitor",
        "other",
    ] = "other"

    relationship: str | None = Field(
        default=None,
        max_length=100,
    )

    preferred_language: str = Field(
        default="English",
        min_length=1,
        max_length=50,
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
    )

    active: bool = True

    @field_validator("name", "preferred_language")
    @classmethod
    def clean_required_text(cls, value: str):
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Value cannot be empty")

        return cleaned


@router.get("/person/status")
def person_status():
    return person_engine.status_info()


@router.get("/persons")
def get_persons():
    persons = registry.all()

    return {
        "status": "ready",
        "count": len(persons),
        "persons": persons,
    }


@router.get("/persons/{person_id}")
def get_person(person_id: str):
    person = registry.get(person_id)

    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    return {
        "status": "ready",
        "person": person,
    }


@router.post(
    "/persons",
    status_code=status.HTTP_201_CREATED,
)
def create_person(payload: PersonCreateRequest):
    person = registry.create(
        name=payload.name,
        category=payload.category,
        relationship=payload.relationship,
        preferred_language=payload.preferred_language,
        notes=payload.notes,
        active=payload.active,
    )

    return {
        "status": "created",
        "person": person,
    }


@router.post("/persons/{person_id}/enroll-current")
def enroll_current_frame(person_id: str):
    person = registry.get(person_id)

    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    frame = frame_buffer.get()

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera frame is not available",
        )

    result = face_enrollment.enroll(
        person_id=person_id,
        frame=frame.copy(),
    )

    if result.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result,
        )

    return result


@router.get("/identity/status")
def identity_status():
    return identity_engine.status()


@router.get("/identity/current")
def identity_current():
    return identity_engine.current()
