from __future__ import annotations

import audioop
import queue
import threading
import time
from typing import Any

from .engine import voice_os_engine
from .wakeword import wakeword_engine
from services.halo_voice_intelligence.stt_service import stt_service


class LiveVoicePipeline:
    def __init__(self) -> None:
        self.config = {
            "sample_rate": 16000,
            "channels": 1,
            "block_size": 1600,
            "input_device": None,
            "session_id": "voice-live",
            "auto_speak": True,

            # Voice tuning
            "speech_threshold": 180,
            "silence_seconds": 1.2,
            "max_record_seconds": 6.0,
            "min_record_seconds": 1.0,
        }

        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()

        self.audio_queue: queue.Queue[bytes] = queue.Queue(
            maxsize=128
        )

        self.state = "stopped"
        self.last_error: str | None = None
        self.last_result: dict[str, Any] | None = None
        self.last_transcript: str | None = None

        self._processing = False
        self._last_processed_text = ""
        self._last_processed_at = 0.0

    def configure(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        for key in self.config:
            if key in payload:
                self.config[key] = payload[key]

        return self.status()

    def start(self) -> dict[str, Any]:
        if self.thread and self.thread.is_alive():
            return self.status()

        self.stop_event.clear()
        self.last_error = None

        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="NoorLiveVoicePipeline",
        )
        self.thread.start()

        return self.status()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.state = "stopping"

        if (
            self.thread
            and self.thread.is_alive()
            and self.thread is not threading.current_thread()
        ):
            self.thread.join(timeout=2.0)

        return self.status()

    @staticmethod
    def _rms(chunk: bytes) -> int:
        if not chunk:
            return 0

        try:
            return int(audioop.rms(chunk, 2))
        except Exception:
            return 0

    def _run(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:
            self.state = "error"
            self.last_error = (
                f"sounddevice unavailable: {exc}"
            )
            return

        sample_rate = int(
            self.config["sample_rate"]
        )
        block_size = int(
            self.config["block_size"]
        )
        channels = int(
            self.config["channels"]
        )

        threshold = int(
            self.config["speech_threshold"]
        )

        silence_seconds = float(
            self.config["silence_seconds"]
        )

        max_record_seconds = float(
            self.config["max_record_seconds"]
        )

        min_record_seconds = float(
            self.config["min_record_seconds"]
        )

        block_seconds = (
            block_size / float(sample_rate)
        )

        silence_blocks_needed = max(
            1,
            int(silence_seconds / block_seconds),
        )

        max_blocks = max(
            1,
            int(max_record_seconds / block_seconds),
        )

        min_blocks = max(
            1,
            int(min_record_seconds / block_seconds),
        )

        self.state = "listening"

        recording = False
        speech_chunks: list[bytes] = []
        silence_blocks = 0

        def callback(
            indata,
            frames,
            time_info,
            status,
        ) -> None:
            if status:
                self.last_error = str(status)

            chunk = bytes(indata)

            try:
                self.audio_queue.put_nowait(chunk)
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(chunk)
                except Exception:
                    pass

        try:
            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=block_size,
                channels=channels,
                dtype="int16",
                device=self.config["input_device"],
                callback=callback,
            ):
                while not self.stop_event.is_set():
                    try:
                        chunk = self.audio_queue.get(
                            timeout=0.25
                        )
                    except queue.Empty:
                        continue

                    level = self._rms(chunk)

                    if not recording:
                        if level >= threshold:
                            recording = True
                            speech_chunks = [chunk]
                            silence_blocks = 0

                        continue

                    speech_chunks.append(chunk)

                    if level >= threshold:
                        silence_blocks = 0
                    else:
                        silence_blocks += 1

                    enough_audio = (
                        len(speech_chunks) >= min_blocks
                    )

                    speech_finished = (
                        enough_audio
                        and silence_blocks
                        >= silence_blocks_needed
                    )

                    maximum_reached = (
                        len(speech_chunks) >= max_blocks
                    )

                    if (
                        speech_finished
                        or maximum_reached
                    ):
                        audio = b"".join(
                            speech_chunks
                        )

                        recording = False
                        speech_chunks = []
                        silence_blocks = 0

                        self._process_audio(
                            audio,
                            sample_rate,
                            channels,
                        )

        except Exception as exc:
            self.state = "error"
            self.last_error = (
                f"{type(exc).__name__}: {exc}"
            )
            return

        self.state = "stopped"

    def _process_audio(
        self,
        audio: bytes,
        sample_rate: int,
        channels: int,
    ) -> None:
        if self._processing:
            return

        self._processing = True
        self.state = "processing"

        try:
            result = stt_service.transcribe(
                audio,
                sample_rate=sample_rate,
                channels=channels,
                backend="auto",
            )

            text = str(
                result.get("text") or ""
            ).strip()

            self.last_transcript = text

            if not text:
                self.last_result = {
                    "status": "no_speech",
                    "stt": result,
                }
                return

            normalized = text.casefold().strip()

            # Prevent the same sentence from being
            # processed repeatedly.
            now = time.monotonic()

            if (
                normalized == self._last_processed_text
                and now - self._last_processed_at < 3.0
            ):
                self.last_result = {
                    "status": "duplicate",
                    "transcript": text,
                }
                return

            self._last_processed_text = normalized
            self._last_processed_at = now

            self.last_result = self.submit_transcript(
                text
            )

        except Exception as exc:
            self.last_error = (
                f"{type(exc).__name__}: {exc}"
            )

            self.last_result = {
                "status": "error",
                "error": self.last_error,
            }

        finally:
            self._processing = False

            if not self.stop_event.is_set():
                self.state = "listening"

    def submit_transcript(
        self,
        text: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        clean = text.strip()

        if not clean:
            raise ValueError(
                "Transcript is empty."
            )

        wake = wakeword_engine.detect_text(
            clean
        )

        wake_only = {
            "noor",
            "hey noor",
            "hello noor",
        }

        if (
            wake.detected
            and clean.casefold().strip() in wake_only
        ):
            self.last_result = {
                "status": "awake",
                "reply": "Ji, main sun rahi hoon.",
                "transcript": clean,
            }

            return self.last_result

        if (
            not wakeword_engine.is_armed()
            and not wake.detected
        ):
            self.last_result = {
                "status": "ignored",
                "reply": "",
                "reason": (
                    "Noor wake word not detected."
                ),
                "transcript": clean,
            }

            return self.last_result

        command_text = clean

        if wake.detected and wake.phrase:
            command_text = clean[
                len(wake.phrase):
            ].strip(" ,:-")

        if not command_text:
            self.last_result = {
                "status": "awake",
                "reply": "Ji, main sun rahi hoon.",
                "transcript": clean,
            }
            return self.last_result

        result = voice_os_engine.process(
            command_text,
            session_id=str(
                self.config["session_id"]
            ),
            confirm=confirm,
            speak=bool(
                self.config["auto_speak"]
            ),
        )

        if result.get("status") == "ok":
            wakeword_engine.disarm()

        self.last_result = {
            **result,
            "transcript": clean,
        }

        return self.last_result

    def status(self) -> dict[str, Any]:
        return {
            "status": self.state,
            "thread_alive": bool(
                self.thread
                and self.thread.is_alive()
            ),
            "config": dict(self.config),
            "queued_audio_chunks":
                self.audio_queue.qsize(),
            "last_transcript":
                self.last_transcript,
            "last_result":
                self.last_result,
            "last_error":
                self.last_error,
        }


live_voice_pipeline = LiveVoicePipeline()