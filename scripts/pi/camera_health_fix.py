"""
Pi Camera Service — health fix summary
========================================

ROOT CAUSE: The /health endpoint called health_service.get_status()
which did not exist on HealthService (only snapshot() existed).
This raised AttributeError → HTTP 500.

FIX: Added get_status() to HealthService that reads from
shared.camera_state (the runtime state updated by the capture loop).
Does NOT open a second cv2.VideoCapture device.

See: services/health_service/health.py (Pi repo @ 3cf5e51)
"""
