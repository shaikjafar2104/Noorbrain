import threading


class FrameBuffer:

    def __init__(self):

        self._frame = None
        self._lock = threading.Lock()

    def update(self, frame):

        with self._lock:
            self._frame = frame

    def get(self):

        with self._lock:
            return self._frame


frame_buffer = FrameBuffer()
