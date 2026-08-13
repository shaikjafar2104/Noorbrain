from fastapi import APIRouter
from services.unified_device_runtime.service import unified_device_runtime

router=APIRouter(prefix="/api/mobile-v3/devices",tags=["devices"])

@router.get("")
def devices():
    items = unified_device_runtime.list_devices()
    return {"status": "ok", "count": len(items), "devices": items}
