from __future__ import annotations

from typing import Any

from .embedding import cosine_similarity, image_to_embedding, normalize
from .store import face_identity_store


class FaceIdentityService:
    def enroll_embedding(
        self,
        *,
        person_id: str,
        embedding: list[float],
        source: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        person = face_identity_store.get_person(person_id)

        if person is None:
            raise KeyError("Person not found.")

        sample = face_identity_store.add_sample({
            "person_id": person_id,
            "embedding": normalize(embedding),
            "source": source,
            "metadata": metadata,
        })

        return {
            "status": "enrolled",
            "person": person,
            "sample": sample,
        }

    def enroll_image(
        self,
        *,
        person_id: str,
        image_base64: str,
        source: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        extracted = image_to_embedding(image_base64)

        return {
            **self.enroll_embedding(
                person_id=person_id,
                embedding=extracted["embedding"],
                source=source,
                metadata={
                    **metadata,
                    "face_detected": extracted["face_detected"],
                    "face_width": extracted["width"],
                    "face_height": extracted["height"],
                },
            ),
            "image_analysis": {
                key: value
                for key, value in extracted.items()
                if key != "embedding"
            },
        }

    def recognize(
        self,
        *,
        embedding: list[float],
        threshold: float,
        zone: str | None,
        track_id: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        candidate = normalize(embedding)
        samples = face_identity_store.list_samples()

        best_sample = None
        best_score = -1.0

        for sample in samples:
            try:
                score = cosine_similarity(
                    candidate,
                    list(sample.get("embedding") or []),
                )
            except Exception:
                continue

            if score > best_score:
                best_score = score
                best_sample = sample

        recognized = (
            best_sample is not None
            and best_score >= threshold
        )

        person = (
            face_identity_store.get_person(
                str(best_sample["person_id"])
            )
            if recognized
            else None
        )

        event = face_identity_store.add_event({
            "recognized": recognized,
            "person_id": person.get("id") if person else None,
            "person_name": person.get("name") if person else None,
            "confidence": round(max(0.0, best_score), 6),
            "threshold": threshold,
            "zone": zone,
            "track_id": track_id,
            "metadata": metadata,
        })

        self._mirror_event(event)

        return {
            "status": "recognized" if recognized else "unknown",
            "recognized": recognized,
            "person": person,
            "confidence": event["confidence"],
            "threshold": threshold,
            "event": event,
        }

    def recognize_image(
        self,
        *,
        image_base64: str,
        threshold: float,
        zone: str | None,
        track_id: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        extracted = image_to_embedding(image_base64)
        result = self.recognize(
            embedding=extracted["embedding"],
            threshold=threshold,
            zone=zone,
            track_id=track_id,
            metadata={
                **metadata,
                "face_detected": extracted["face_detected"],
            },
        )
        result["image_analysis"] = {
            key: value
            for key, value in extracted.items()
            if key != "embedding"
        }
        return result

    @staticmethod
    def _mirror_event(event: dict[str, Any]) -> None:
        try:
            from services.vision_intelligence.store import vision_event_store

            vision_event_store.add({
                "event_type": (
                    "face_recognized"
                    if event.get("recognized")
                    else "unknown_face"
                ),
                "source": "face_identity",
                "zone": event.get("zone"),
                "person_id": event.get("person_id"),
                "confidence": event.get("confidence"),
                "message": (
                    f"Recognized {event.get('person_name')}."
                    if event.get("recognized")
                    else "Unknown face detected."
                ),
                "snapshot_path": None,
                "metadata": {
                    "track_id": event.get("track_id"),
                    **dict(event.get("metadata") or {}),
                },
            })
        except Exception:
            pass


face_identity_service = FaceIdentityService()
