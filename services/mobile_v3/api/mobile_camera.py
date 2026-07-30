from fastapi import APIRouter

router=APIRouter(prefix="/api/mobile-v3/camera",tags=["camera"])

CAMERAS=[

{
"id":"hall",
"name":"Hall Camera",
"stream":"/video_feed",
"online":True
}

]

@router.get("")
def camera():

    return {"cameras":CAMERAS}

