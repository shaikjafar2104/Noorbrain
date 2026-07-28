from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from .noise_filter import NoiseFilter
from .vad import VoiceActivityDetector


class AudioPipeline:
    def __init__(self) -> None:
        self.noise_filter = NoiseFilter()
        self.vad = VoiceActivityDetector()

    def prepare(self, source: Path) -> Dict[str, Any]:
        output = source.with_name(source.stem + "-clean.wav")
        filtered = self.noise_filter.process(source, output)
        if filtered.get("status") != "ok":
            return {"status": "unavailable", "filter": filtered}
        vad = self.vad.analyze_wav(output)
        return {"status": "ok", "audio_path": str(output), "filter": filtered, "vad": vad}
