
async function api(url){

return fetch(url).then(r=>r.json())

}

async function load(){

const data=await api("/api/mobile-v3/home")

document.getElementById("camera-card").innerHTML=

"<h3>📷 "+data.camera.title+"</h3>"

document.getElementById("quick-actions").innerHTML=`

<button onclick="location.href='#camera'">Camera</button>

<button onclick="location.href='#halo'">HALO</button>

<button onclick="location.href='#rooms'">Rooms</button>

<button onclick="location.href='#devices'">Devices</button>

<button onclick="location.href='#automation'">Automation</button>

<button onclick="location.href='#settings'">Settings</button>

`

}

load()

