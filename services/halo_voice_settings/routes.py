from pathlib import Path
import json
from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/halo-voice-settings", tags=["HALO Voice Settings"])
ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "halo_voice_settings.json"
DEFAULTS = {"voice_name":"","voice_lang":"","rate":1.0,"pitch":1.0,"volume":1.0,"enabled":True}

def read_settings():
    STORE.parent.mkdir(parents=True, exist_ok=True)
    if not STORE.exists():
        STORE.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
        return DEFAULTS.copy()
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    result = DEFAULTS.copy()
    if isinstance(data, dict):
        result.update(data)
    return result

def write_settings(data):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, indent=2), encoding="utf-8")

@router.get("/health")
async def health():
    return {"status":"healthy","service":"halo_voice_settings","version":"1.0.0"}

@router.get("")
async def get_settings():
    return {"status":"ok","settings":read_settings()}

@router.post("")
async def update_settings(payload: dict = Body(...)):
    data = read_settings()
    data.update({
        "voice_name": str(payload.get("voice_name", data["voice_name"])),
        "voice_lang": str(payload.get("voice_lang", data["voice_lang"])),
        "rate": max(.5, min(2.0, float(payload.get("rate", data["rate"])))),
        "pitch": max(.5, min(2.0, float(payload.get("pitch", data["pitch"])))),
        "volume": max(0.0, min(1.0, float(payload.get("volume", data["volume"])))),
        "enabled": bool(payload.get("enabled", data["enabled"])),
    })
    write_settings(data)
    return {"status":"updated","settings":data}
