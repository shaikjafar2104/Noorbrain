from pathlib import Path

import numpy as np

from services.person_ai.face_models import face_models
from services.person_ai.person_registry import registry


class FaceEnrollment:
    def __init__(self):
        self.base = Path("data/person_profiles/faces")
        self.base.mkdir(parents=True, exist_ok=True)

    def enroll(self, person_id: str, frame):
        person = registry.get(person_id)

        if person is None:
            return {
                "status": "error",
                "message": "Person not found",
            }

        faces = face_models.detect(frame)

        if len(faces) != 1:
            return {
                "status": "error",
                "faces_detected": len(faces),
                "message": "Exactly one face is required",
            }

        embedding = face_models.extract_embedding(
            frame,
            faces[0],
        )

        person_folder = self.base / person_id
        person_folder.mkdir(parents=True, exist_ok=True)

        samples = sorted(person_folder.glob("*.npy"))
        sample_number = len(samples) + 1

        sample_file = person_folder / f"{sample_number:03d}.npy"

        np.save(
            sample_file,
            embedding.astype(np.float32),
        )

        updated_person = registry.update_face_info(
            person_id,
            sample_number,
        )

        return {
            "status": "success",
            "person_id": person_id,
            "person": updated_person,
            "sample": sample_number,
            "sample_file": sample_file.name,
        }


face_enrollment = FaceEnrollment()
