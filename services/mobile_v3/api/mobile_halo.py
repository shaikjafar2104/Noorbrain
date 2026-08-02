from fastapi import APIRouter

router=APIRouter(prefix="/api/mobile-v3/halo",tags=["halo"])

@router.get("/status")
def status():

    return {

        "assistant":"HALO",

        "voice":True,

        "chat":True,

        "wakeword":False,

        "online":True

    }

