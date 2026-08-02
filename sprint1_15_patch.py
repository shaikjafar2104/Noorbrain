from pathlib import Path

html=Path("dashboard/mobile/index.html")
js=Path("dashboard/js/mobile-v2.js")
css=Path("dashboard/css/mobile-v2.css")

H=html.read_text(encoding="utf-8")
J=js.read_text(encoding="utf-8")
C=css.read_text(encoding="utf-8")

if "nbv2HomeGrid" not in H:

    card="""

<section id="nbv2HomeGrid" class="nbv2-home-grid">

<button class="nbv2-home-card" onclick="gotoPage('camera')">📷<span>Camera</span></button>

<button class="nbv2-home-card" onclick="gotoPage('halo')">🤖<span>HALO</span></button>

<button class="nbv2-home-card" onclick="gotoPage('rooms')">🏠<span>Rooms</span></button>

<button class="nbv2-home-card" onclick="gotoPage('devices')">💡<span>Devices</span></button>

<button class="nbv2-home-card" onclick="gotoPage('automation')">⚡<span>Automation</span></button>

<button class="nbv2-home-card" onclick="gotoPage('settings')">⚙<span>Settings</span></button>

</section>

"""

    H=H.replace("</main>",card+"\n</main>")

if "function gotoPage" not in J:

    J+="""


function gotoPage(page){

const map={

camera:'.nbv2-camera-section',

halo:'#nbv2Halo',

rooms:'.nbv2-room-section',

devices:'.nbv2-device-section',

automation:'.nbv2-automation-section',

settings:'.nbv2-settings-section'

}

const t=document.querySelector(map[page])

if(t){

t.scrollIntoView({behavior:'smooth'})

}

}

"""

if ".nbv2-home-grid" not in C:

    C+="""

.nbv2-home-grid{

display:grid;

grid-template-columns:repeat(3,1fr);

gap:14px;

margin-top:18px;

}

.nbv2-home-card{

height:110px;

border-radius:18px;

background:#1b2b48;

display:flex;

flex-direction:column;

justify-content:center;

align-items:center;

font-size:30px;

font-weight:700;

color:white;

}

.nbv2-home-card span{

margin-top:8px;

font-size:14px;

}

"""

html.write_text(H,encoding="utf-8")
js.write_text(J,encoding="utf-8")
css.write_text(C,encoding="utf-8")

print("SPRINT 1.15 COMPLETE")
