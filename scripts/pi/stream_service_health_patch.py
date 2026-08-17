"""
Pi Camera Service — /health fix reference
==========================================

ROOT CAUSE: The /health endpoint in stream_service/stream.py called
health_service.get_status(), but HealthService only had a snapshot()
method — no get_status() method existed. This caused AttributeError
→ HTTP 500.

FIX APPLIED (committed to shaikjafar2104/NoorCameraNode-.git @ 3cf5e51):

In services/health_service/health.py, HealthService now exposes:

    def get_status(self):
        \"\"\"Lightweight health summary for the /health endpoint.

        Reads already-running camera_service/runtime state only.
        Does NOT open a second camera device.
        \"\"\"
        camera = camera_state.to_dict()
        last_frame_age = round(time.time() - camera_state.last_frame_time, 1)
        return {
            "status": "healthy" if camera["connected"] else "degraded",
            "camera_connected": camera["connected"],
            "running": camera["connected"],
            "fps": camera["fps"],
            "resolution": camera["resolution"],
            "last_frame_age": last_frame_age,
            "frames": camera["frames"],
            "dropped_frames": camera["dropped_frames"],
            "reconnects": camera["reconnects"],
            "uptime": camera["uptime"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

And in stream_service/stream.py, /health now delegates:

    @app.get("/health")
    def health():
        return health_service.get_status()

This reads from shared.camera_state (updated by the running CameraService
capture loop) — it NEVER opens a second cv2.VideoCapture device.

Verified live on Pi:
  GET http://192.168.2.29:8000/health → HTTP 200
  status=healthy, camera_connected=true, running=true, fps>0
"""
