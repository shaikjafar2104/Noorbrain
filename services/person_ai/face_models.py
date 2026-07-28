from pathlib import Path
from threading import RLock

import cv2
import numpy as np


class FaceModels:
    def __init__(self):
        self.detector_model = Path(
            "models/faces/face_detection_yunet.onnx"
        )
        self.recognizer_model = Path(
            "models/faces/face_recognition_sface.onnx"
        )

        self.lock = RLock()
        self.detector = None
        self.recognizer = None
        self.input_size = (320, 320)

        self._load()

    def _load(self):
        if not self.detector_model.exists():
            raise FileNotFoundError(
                f"Missing model: {self.detector_model}"
            )

        if not self.recognizer_model.exists():
            raise FileNotFoundError(
                f"Missing model: {self.recognizer_model}"
            )

        self.detector = cv2.FaceDetectorYN.create(
            str(self.detector_model),
            "",
            self.input_size,
            0.85,
            0.3,
            5000,
        )

        self.recognizer = cv2.FaceRecognizerSF.create(
            str(self.recognizer_model),
            "",
        )

    def detect(self, frame: np.ndarray):
        if frame is None or frame.size == 0:
            return []

        height, width = frame.shape[:2]

        with self.lock:
            self.detector.setInputSize((width, height))
            _, faces = self.detector.detect(frame)

        if faces is None:
            return []

        return faces

    def extract_embedding(
        self,
        frame: np.ndarray,
        face: np.ndarray,
    ):
        with self.lock:
            aligned = self.recognizer.alignCrop(frame, face)
            feature = self.recognizer.feature(aligned)

        embedding = np.asarray(feature, dtype=np.float32).flatten()

        norm = np.linalg.norm(embedding)

        if norm > 0:
            embedding = embedding / norm

        return embedding

    def cosine_similarity(
        self,
        first: np.ndarray,
        second: np.ndarray,
    ) -> float:
        first = np.asarray(first, dtype=np.float32).reshape(1, -1)
        second = np.asarray(second, dtype=np.float32).reshape(1, -1)

        return float(
            self.recognizer.match(
                first,
                second,
                cv2.FaceRecognizerSF_FR_COSINE,
            )
        )

    def status(self):
        return {
            "status": "ready",
            "opencv_version": cv2.__version__,
            "detector": self.detector_model.name,
            "recognizer": self.recognizer_model.name,
            "detector_loaded": self.detector is not None,
            "recognizer_loaded": self.recognizer is not None,
        }


face_models = FaceModels()
