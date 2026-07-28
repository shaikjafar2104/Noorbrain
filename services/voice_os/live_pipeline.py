from __future__ import annotations
import queue
import threading
import time
from typing import Any

from .engine import voice_os_engine
from .wakeword import wakeword_engine

class LiveVoicePipeline:
    def __init__(self) -> None:
        self.config = {
            "sample_rate": 16000,
            "channels": 1,
            "block_size": 1600,
            "input_device": None,
            "session_id": "voice-live",
            "auto_speak": True,
        }
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=128)
        self.state = "stopped"
        self.last_error: str | None = None
        self.last_result: dict[str, Any] | None = None

    def configure(self, payload: dict[str, Any]) -> dict[str, Any]:
        for key in self.config:
            if key in payload:
                self.config[key] = payload[key]
        return self.status()

    def start(self) -> dict[str, Any]:
        if self.thread and self.thread.is_alive():
            return self.status()
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.state = "stopping"
        return self.status()

    def _run(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:
            self.state = "error"
            self.last_error = f"sounddevice unavailable: {exc}"
            return

        self.state = "listening"

        def callback(indata, frames, time_info, status) -> None:
            if status:
                self.last_error = str(status)
            try:
                self.audio_queue.put_nowait(bytes(indata))
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(bytes(indata))
                except Exception:
                    pass

        try:
            with sd.RawInputStream(
                samplerate=int(self.config["sample_rate"]),
                blocksize=int(self.config["block_size"]),
                channels=int(self.config["channels"]),
                dtype="int16",
                device=self.config["input_device"],
                callback=callback,
            ):
                while not self.stop_event.is_set():
                    time.sleep(0.1)
        except Exception as exc:
            self.state = "error"
            self.last_error = f"{type(exc).__name__}: {exc}"
            return

        self.state = "stopped"

    def submit_transcript(self, text: str, confirm: bool = False) -> dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise ValueError("Transcript is empty.")

        wake = wakeword_engine.detect_text(clean)

        if wake.detected and clean.casefold().strip() in {"halo", "hey halo", "hello halo"}:
            self.last_result = {"status": "awake", "reply": "Ji Shaik."}
            return self.last_result

        if not wakeword_engine.is_armed() and not wake.detected:
            self.last_result = {
                "status": "ignored",
                "reply": "",
                "reason": "Wake word not detected.",
            }
            return self.last_result

        command_text = clean
        if wake.detected and wake.phrase:
            command_text = clean[len(wake.phrase):].strip(" ,:-")

        result = voice_os_engine.process(
            command_text,
            session_id=str(self.config["session_id"]),
            confirm=confirm,
            speak=bool(self.config["auto_speak"]),
        )

        if result.get("status") == "ok":
            wakeword_engine.disarm()

        self.last_result = result
        return result

    def status(self) -> dict[str, Any]:
        return {
            "status": self.state,
            "thread_alive": bool(self.thread and self.thread.is_alive()),
            "config": dict(self.config),
            "queued_audio_chunks": self.audio_queue.qsize(),
            "last_result": self.last_result,
            "last_error": self.last_error,
        }

live_voice_pipeline = LiveVoicePipeline()
