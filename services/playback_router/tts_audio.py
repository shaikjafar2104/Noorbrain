from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIPER = ROOT / "tools" / "piper" / "piper"
DEFAULT_PIPER_MODEL = ROOT / "models" / "voice" / "en_US-lessac-medium.onnx"


class TTSAudioError(RuntimeError):
    pass


def _piper_command() -> tuple[str, Path] | None:
    configured = os.getenv("PIPER_EXECUTABLE", "").strip()
    executable = configured or shutil.which("piper") or (str(DEFAULT_PIPER) if DEFAULT_PIPER.is_file() else "")
    configured_model = os.getenv("PIPER_MODEL_PATH", "").strip()
    model = Path(configured_model) if configured_model else DEFAULT_PIPER_MODEL
    if not executable or not model.is_file():
        return None
    return executable, model


def _run_piper(text: str, output: Path) -> dict[str, Any] | None:
    resolved = _piper_command()
    if not resolved:
        return None
    executable, model = resolved
    environment = os.environ.copy()
    bundled_library = DEFAULT_PIPER.parent
    if Path(executable).resolve() == DEFAULT_PIPER.resolve():
        existing = environment.get("LD_LIBRARY_PATH", "")
        environment["LD_LIBRARY_PATH"] = str(bundled_library) + (":" + existing if existing else "")
    completed = subprocess.run(
        [executable, "--model", str(model), "--output_file", str(output)],
        input=text.encode("utf-8"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
        env=environment,
    )
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        return None
    return {"engine": "piper", "model": model.name}


def _run_espeak(text: str, output: Path) -> dict[str, Any] | None:
    executable = shutil.which("espeak-ng") or shutil.which("espeak")
    if not executable:
        return None
    completed = subprocess.run(
        [executable, "-w", str(output), text],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        return None
    return {"engine": Path(executable).name}


def synthesize_tts_audio(text: str) -> tuple[bytes, str, dict[str, Any]]:
    """Render speech to bytes without opening or writing to a local audio device."""

    clean = str(text or "").strip()
    if not clean:
        raise ValueError("Text message is required")
    if len(clean) > 4000:
        raise ValueError("Text message is too long")

    with tempfile.TemporaryDirectory(prefix="noorbrain-tts-") as directory:
        output = Path(directory) / "message.wav"
        metadata = _run_piper(clean, output) or _run_espeak(clean, output)
        if not metadata:
            raise TTSAudioError("No server TTS renderer is available")
        audio = output.read_bytes()

    if len(audio) < 44:
        raise TTSAudioError("TTS renderer returned invalid audio")
    return audio, "wav", metadata
