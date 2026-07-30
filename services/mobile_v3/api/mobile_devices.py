from fastapi import APIRouter

router=APIRouter(prefix="/api/mobile-v3/devices",tags=["devices"])

DEVICES=[

{"id":"light","name":"Hall Light","state":"off"},

{"id":"fan","name":"Hall Fan","state":"off"},

{"id":"tv","name":"Living TV","state":"off"},

{"id":"ac","name":"Bedroom AC","state":"off"}

]

@router.get("")
def devices():

    return {"devices":DEVICES}

