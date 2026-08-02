from fastapi import APIRouter
from services.mobile_v3.core.config import layout

router=APIRouter(prefix="/api/mobile-v3",tags=["mobile-v3"])

@router.get("/layout")
def get_layout():
    return layout()

@router.get("/health")
def health():
    return {"status":"ok","version":"3.0"}
