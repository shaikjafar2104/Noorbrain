from fastapi import APIRouter

router=APIRouter(prefix="/api/mobile-v3/rooms",tags=["rooms"])

ROOMS=[

{"id":"hall","name":"Hall","icon":"🛋️"},

{"id":"kitchen","name":"Kitchen","icon":"🍳"},

{"id":"bedroom","name":"Bedroom","icon":"🛏️"},

{"id":"prayer","name":"Prayer Room","icon":"🕌"},

{"id":"garage","name":"Garage","icon":"🚗"}

]

@router.get("")
def rooms():

    return {"rooms":ROOMS}

