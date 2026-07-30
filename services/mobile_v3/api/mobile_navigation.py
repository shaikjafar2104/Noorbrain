from fastapi import APIRouter

router=APIRouter(prefix="/api/mobile-v3/navigation",tags=["mobile-navigation"])

@router.get("")
def navigation():

    return {

        "bottom":[

            {
                "id":"home",
                "title":"Home",
                "icon":"house"
            },

            {
                "id":"rooms",
                "title":"Rooms",
                "icon":"grid"
            },

            {
                "id":"camera",
                "title":"Camera",
                "icon":"camera"
            },

            {
                "id":"halo",
                "title":"HALO",
                "icon":"mic"
            },

            {
                "id":"automation",
                "title":"Automation",
                "icon":"bolt"
            },

            {
                "id":"devices",
                "title":"Devices",
                "icon":"cpu"
            },

            {
                "id":"settings",
                "title":"Settings",
                "icon":"gear"
            }

        ]

    }
