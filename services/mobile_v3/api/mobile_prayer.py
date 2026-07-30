from fastapi import APIRouter

router=APIRouter(prefix="/api/mobile-v3/prayer",tags=["prayer"])

@router.get("")
def prayer():

    return {

        "current":"Asr",

        "next":"Maghrib",

        "countdown":"01:12:44"

    }

