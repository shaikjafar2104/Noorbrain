from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .device_config import voice_device_config


class OfflineTTS:
    def health(self) -> dict[str, Any]:
        piper = shutil.which("piper")
        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        aplay = shutil.which("aplay")

        available = []
        if piper:
            available.append("piper")
        if espeak:
            available.append("espeak")
        if aplay:
            available.append("aplay")

        return {
            "status": "healthy" if (piper or espeak) else "degraded",
            "available_backends": available,
            "piper_model": self._piper_model(),
            "config": voice_device_config.read(),
        }

    @staticmethod
    def _piper_model() -> str | None:
        import os
        model = os.getenv("PIPER_MODEL_PATH", "").strip()
        return model or None

    def speak(
        self,
        text: str,
        *,
        backend: str | None = None,
    ) -> dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise ValueError("TTS text is empty.")

        config = voice_device_config.read()
        backend = str(backend or config.get("tts_backend", "auto"))

        if backend in {"auto", "piper"}:
            result = self._piper(clean)
            if result["status"] == "ok" or backend == "piper":
                return result

        if backend in {"auto", "espeak"}:
            return self._espeak(clean)

        return {
            "status": "unavailable",
            "backend": backend,
            "reason": f"Unsupported TTS backend: {backend}",
        }

    def _piper(self, text: str) -> dict[str, Any]:
        executable = shutil.which("piper")
        model = self._piper_model()
        player = shutil.which("aplay")

        if not executable:
            return {
                "status": "unavailable",
                "backend": "piper",
                "reason": "piper executable not found.",
            }

        if not model or not Path(model).is_file():
            return {
                "status": "unavailable",
                "backend": "piper",
                "reason": "PIPER_MODEL_PATH is not configured.",
            }

        with tempfile.TemporaryDirectory() as directory:
            wav_path = Path(directory) / "halo.wav"

            try:
                completed = subprocess.run(
                    [
                        executable,
                        "--model",
                        model,
                        "--output_file",
                        str(wav_path),
                    ],
                    input=text.encode("utf-8"),
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
            except Exception as exc:
                return {
                    "status": "error",
                    "backend": "piper",
                    "reason": f"{type(exc).__name__}: {exc}",
                }

            if completed.returncode != 0:
                return {
                    "status": "error",
                    "backend": "piper",
                    "reason": completed.stderr.decode("utf-8", errors="replace"),
                }

            if player:
                subprocess.run(
                    [player, str(wav_path)],
                    capture_output=True,
                    timeout=120,
                    check=False,
                )

        return {
            "status": "ok",
            "backend": "piper",
        }

    @staticmethod
    def _espeak(text: str) -> dict[str, Any]:
        executable = shutil.which("espeak-ng") or shutil.which("espeak")

        if not executable:
            return {
                "status": "unavailable",
                "backend": "espeak",
                "reason": "espeak executable not found.",
            }

        try:
            completed = subprocess.run(
                [executable, text],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except Exception as exc:
            return {
                "status": "error",
                "backend": "espeak",
                "reason": f"{type(exc).__name__}: {exc}",
            }

        return {
            "status": "ok" if completed.returncode == 0 else "error",
            "backend": "espeak",
            "returncode": completed.returncode,
        }


offline_tts = OfflineTTS()
