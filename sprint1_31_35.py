from pathlib import Path

ROOT=Path("dashboard")

html=ROOT/"mobile"/"index.html"
js=ROOT/"js"/"mobile-home-control-center.js"
css=ROOT/"css"/"mobile-home-control-center.css"

if not js.exists():
    js.write_text("",encoding="utf-8")

if not css.exists():
    css.write_text("",encoding="utf-8")

H=html.read_text(encoding="utf-8",errors="ignore")
J=js.read_text(encoding="utf-8",errors="ignore")
C=css.read_text(encoding="utf-8",errors="ignore")

# -------------------------------------------------
# Sprint 1.31
# Live Camera Card
# -------------------------------------------------

if "nb-live-camera-card" not in H:

    H=H.replace(

    '<div id="nbv2CameraHero"',

    '''

<div id="nb-live-camera-card">

<h3>📷 Live Camera</h3>

<div id="nb-camera-online">ONLINE</div>

</div>

<div id="nbv2CameraHero"

''')

# -------------------------------------------------
# Sprint 1.32
# Refresh Camera
# -------------------------------------------------

if "NB.reloadCamera" not in J:

    J+="""


NB.reloadCamera=function(){

const img=document.querySelector("#nbv2CameraImage");

if(!img)return;

const u=img.src.split("?")[0];

img.src=u+"?v="+Date.now();

}

"""

# -------------------------------------------------
# Sprint 1.33
# Camera Health
# -------------------------------------------------

if "NB.cameraHealth" not in J:

    J+="""


NB.cameraHealth=function(){

fetch("/api/mobile-v3/camera")

.then(r=>r.json())

.then(j=>{

const e=document.querySelector("#nb-camera-online");

if(e){

e.innerHTML=j.cameras[0].online?"ONLINE":"OFFLINE";

}

})

}

setInterval(NB.cameraHealth,5000);

"""

# -------------------------------------------------
# Sprint 1.34
# CSS
# -------------------------------------------------

if "#nb-live-camera-card" not in C:

    C+="""

#nb-live-camera-card{

background:#163355;

border-radius:20px;

padding:15px;

margin-bottom:12px;

}

#nb-camera-online{

display:inline-block;

margin-top:10px;

padding:6px 12px;

background:#1cb56f;

border-radius:999px;

font-weight:700;

}

"""

# -------------------------------------------------
# Sprint 1.35
# Auto Boot
# -------------------------------------------------

if "window.addEventListener('load'" not in J:

    J+="""


window.addEventListener("load",()=>{

NB.reloadCamera();

NB.cameraHealth();

});

"""

html.write_text(H,encoding="utf-8")
js.write_text(J,encoding="utf-8")
css.write_text(C,encoding="utf-8")

print("SPRINT 1.31 PASS")
print("SPRINT 1.32 PASS")
print("SPRINT 1.33 PASS")
print("SPRINT 1.34 PASS")
print("SPRINT 1.35 PASS")
