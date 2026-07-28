from __future__ import annotations

import base64
import math
from typing import Any


def normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))

    if magnitude <= 1e-12:
        raise ValueError("Embedding magnitude is zero.")

    return [float(value) / magnitude for value in vector]


def cosine_similarity(
    first: list[float],
    second: list[float],
) -> float:
    if len(first) != len(second):
        raise ValueError("Embedding lengths do not match.")

    a = normalize(first)
    b = normalize(second)
    return max(
        -1.0,
        min(1.0, sum(x * y for x, y in zip(a, b))),
    )


def image_to_embedding(image_base64: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image: {exc}") from exc

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            f"OpenCV/NumPy unavailable: {exc}"
        ) from exc

    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)

    if image is None:
        raise ValueError("Unable to decode image.")

    face = _extract_face(image, cv2)

    resized = cv2.resize(
        face,
        (32, 32),
        interpolation=cv2.INTER_AREA,
    )
    equalized = cv2.equalizeHist(resized)
    vector = equalized.astype("float32").reshape(-1)
    vector = (vector - float(vector.mean())) / (
        float(vector.std()) + 1e-6
    )

    return {
        "embedding": normalize(vector.tolist()),
        "face_detected": face.shape != image.shape,
        "width": int(face.shape[1]),
        "height": int(face.shape[0]),
    }


def _extract_face(image, cv2):
    try:
        cascade_path = (
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )
        cascade = cv2.CascadeClassifier(cascade_path)
        faces = cascade.detectMultiScale(
            image,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40),
        )

        if len(faces):
            x, y, width, height = max(
                faces,
                key=lambda item: int(item[2]) * int(item[3]),
            )
            return image[y:y + height, x:x + width]
    except Exception:
        pass

    return image
