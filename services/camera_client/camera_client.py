"""
============================================================
Project : NoorBrain
Module  : Camera Client
Version : 1.1.0
Purpose : MJPEG camera client with asynchronous identity AI
============================================================
"""

import threading
import time

import cv2
import numpy as np
import requests

from shared.config_manager import load_config
from shared.frame_buffer import frame_buffer
from shared.logger import logger
from services.person_ai.identity_engine import identity_engine


class CameraClient:

    def __init__(self):
        config = load_config()
        camera_node = config.get("camera_node", {})

        self.base_url = camera_node.get(
            "url",
            "http://127.0.0.1:8000",
        )
        self.stream_url = self.base_url + "/video_feed"

        self.connected = False
        self.running = False

        self.thread = None
        self.identity_thread = None

        self.session = requests.Session()

        self.frame_count = 0
        self.current_fps = 0.0
        self.last_fps_time = time.time()
        self.last_frame_time = 0.0

        self.identity_interval = 1.0
        self.identity_last_run = 0.0
        self.identity_frame = None
        self.identity_lock = threading.Lock()
        self.identity_event = threading.Event()

        logger.info("Camera URL : %s", self.base_url)

    # ----------------------------------------------------
    def connect(self):
        logger.info("=" * 60)
        logger.info("Connecting to Camera Node")
        logger.info("=" * 60)

        while self.running:
            try:
                response = self.session.get(
                    self.stream_url,
                    stream=True,
                    timeout=10,
                )

                if response.status_code == 200:
                    self.connected = True
                    logger.info("Camera Stream Connected")
                    return response

                logger.warning(
                    "Camera HTTP status: %s",
                    response.status_code,
                )

                response.close()

            except requests.RequestException as error:
                logger.warning(
                    "Camera connection failed: %s",
                    error,
                )

            self.connected = False
            logger.info("Retrying camera in 3 seconds...")
            time.sleep(3)

        return None

    # ----------------------------------------------------
    def receive_stream(self):
        while self.running:
            response = self.connect()

            if response is None:
                continue

            try:
                buffer = b""

                for chunk in response.iter_content(4096):
                    if not self.running:
                        break

                    if not chunk:
                        continue

                    buffer += chunk

                    while True:
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(
                            b"\xff\xd9",
                            start + 2,
                        )

                        if start == -1 or end == -1:
                            break

                        jpg = buffer[start:end + 2]
                        buffer = buffer[end + 2:]

                        self.process_frame(jpg)

            except requests.RequestException as error:
                logger.warning(
                    "Camera stream error: %s",
                    error,
                )
                self.connected = False
                time.sleep(2)

            except Exception:
                logger.exception("Unexpected camera stream error")
                self.connected = False
                time.sleep(2)

            finally:
                try:
                    response.close()
                except Exception:
                    pass

    # ----------------------------------------------------
    def process_frame(self, jpg):
        try:
            image = np.frombuffer(
                jpg,
                dtype=np.uint8,
            )

            frame = cv2.imdecode(
                image,
                cv2.IMREAD_COLOR,
            )

            if frame is None:
                return

            frame_buffer.update(frame)

            now = time.time()
            self.last_frame_time = now
            self.frame_count += 1

            if (
                now - self.identity_last_run
                >= self.identity_interval
            ):
                with self.identity_lock:
                    self.identity_frame = frame.copy()

                self.identity_last_run = now
                self.identity_event.set()

            elapsed = now - self.last_fps_time

            if elapsed >= 1.0:
                self.current_fps = (
                    self.frame_count / elapsed
                )

                logger.info(
                    "Camera FPS : %.2f",
                    self.current_fps,
                )

                self.frame_count = 0
                self.last_fps_time = now

        except Exception:
            logger.exception("Camera frame processing failed")

    # ----------------------------------------------------
    def identity_loop(self):
        logger.info("Identity Camera Worker Started")

        while self.running:
            self.identity_event.wait(timeout=1.0)
            self.identity_event.clear()

            if not self.running:
                break

            with self.identity_lock:
                frame = self.identity_frame
                self.identity_frame = None

            if frame is None:
                continue

            try:
                result = identity_engine.process_frame(frame)

                logger.debug(
                    "Identity frame processed: "
                    "faces=%s recognized=%s unknown=%s",
                    result.get("faces_detected", 0),
                    result.get("recognized_count", 0),
                    result.get("unknown_count", 0),
                )

            except Exception:
                logger.exception(
                    "Identity camera processing failed"
                )

        logger.info("Identity Camera Worker Stopped")

    # ----------------------------------------------------
    def get_frame(self):
        return frame_buffer.get()

    # ----------------------------------------------------
    def is_connected(self):
        return self.connected

    # ----------------------------------------------------
    def fps(self):
        return round(self.current_fps, 2)

    # ----------------------------------------------------
    def start(self):
        if self.running:
            return

        logger.info("=" * 60)
        logger.info("Starting Camera Client")
        logger.info("=" * 60)

        self.running = True

        self.identity_thread = threading.Thread(
            target=self.identity_loop,
            daemon=True,
            name="IdentityCameraWorker",
        )
        self.identity_thread.start()

        self.thread = threading.Thread(
            target=self.receive_stream,
            daemon=True,
            name="CameraClient",
        )
        self.thread.start()

        logger.info("Camera Client Started")

    # ----------------------------------------------------
    def stop(self):
        logger.info("Stopping Camera Client")

        self.running = False
        self.identity_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)

        if (
            self.identity_thread
            and self.identity_thread.is_alive()
        ):
            self.identity_thread.join(timeout=3)

        try:
            self.session.close()
        except Exception:
            pass

        self.connected = False
        logger.info("Camera Client Stopped")

    # ----------------------------------------------------
    def snapshot(self):
        return {
            "connected": self.connected,
            "stream_url": self.stream_url,
            "fps": round(self.current_fps, 2),
            "running": self.running,
            "last_frame": (
                round(
                    time.time() - self.last_frame_time,
                    2,
                )
                if self.last_frame_time
                else None
            ),
            "identity_worker": {
                "running": bool(
                    self.identity_thread
                    and self.identity_thread.is_alive()
                ),
                "interval_seconds": self.identity_interval,
            },
        }


camera_client = CameraClient()


if __name__ == "__main__":
    try:
        camera_client.start()

        while True:
            time.sleep(1)
            print(camera_client.snapshot())

    except KeyboardInterrupt:
        pass

    finally:
        camera_client.stop()
