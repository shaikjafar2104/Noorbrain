from fastapi import APIRouter

router=APIRouter(prefix="/api/mobile-v3/home",tags=["mobile-home"])

@router.get("")
def home():

    return {

        "camera":{
            "enabled":True,
            "title":"Hall Camera",
            "stream":"/video_feed"
        },

        "halo":{
            "enabled":True
        },

        "prayer":{
            "enabled":True
        },

        "family":{
            "enabled":True
        },

        "automation":{
            "enabled":True
        },

        "devices":{
            "enabled":True
        },

        "notifications":{
            "enabled":True
        }

    }
