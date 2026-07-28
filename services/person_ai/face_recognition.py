from pathlib import Path

import numpy as np

from services.person_ai.face_models import face_models
from services.person_ai.person_registry import registry


class FaceRecognition:

    def __init__(self):
        self.base = Path("data/person_profiles/faces")

    def recognize(self, frame):

        faces = face_models.detect(frame)

        if len(faces) == 0:
            return []

        persons = registry.all()

        results = []

        for face in faces:

            embedding = face_models.extract_embedding(
                frame,
                face
            )

            best_score = -1
            best_person = None

            for person in persons:

                folder = self.base / person["person_id"]

                if not folder.exists():
                    continue

                for sample in folder.glob("*.npy"):

                    stored = np.load(sample)

                    score = face_models.cosine_similarity(
                        embedding,
                        stored
                    )

                    if score > best_score:
                        best_score = score
                        best_person = person

            if best_score >= 0.45:

                results.append({
                    "status": "recognized",
                    "confidence": round(best_score * 100, 2),
                    "person": best_person
                })

            else:

                results.append({
                    "status": "unknown",
                    "confidence": round(best_score * 100, 2)
                })

        return results


face_recognition = FaceRecognition()
