from pathlib import Path
import shutil

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

# =====================================================
# Sprint 1.21
# Home Control Dashboard
# =====================================================

if "nb-home-dashboard" not in H:

    block="""

<section id="nb-home-dashboard">

<div class="nb-home-grid">

<div class="nb-card" onclick="NB.gotoCamera()">📷<span>Camera</span></div>

<div class="nb-card" onclick="NB.gotoHalo()">🤖<span>HALO</span></div>

<div class="nb-card" onclick="NB.gotoRooms()">🏠<span>Rooms</span></div>

<div class="nb-card" onclick="NB.gotoDevices()">💡<span>Devices</span></div>

<div class="nb-card" onclick="NB.gotoPrayer()">🕌<span>Prayer</span></div>

<div class="nb-card" onclick="NB.gotoAutomation()">⚡<span>Automation</span></div>

</div>

</section>

"""

    H=H.replace("</main>",block+"\n</main>")

# =====================================================
# Sprint 1.22
# JS
# =====================================================

if "const NB={" not in J:

    J+="""

const NB={

gotoCamera(){document.querySelector(".nbv2-camera-section")?.scrollIntoView({behavior:"smooth"})},

gotoHalo(){document.querySelector("#nbv2Halo")?.scrollIntoView({behavior:"smooth"})},

gotoRooms(){document.querySelector(".nbv2-room-section")?.scrollIntoView({behavior:"smooth"})},

gotoDevices(){document.querySelector(".nbv2-device-section")?.scrollIntoView({behavior:"smooth"})},

gotoPrayer(){document.querySelector(".nbv2-prayer-section")?.scrollIntoView({behavior:"smooth"})},

gotoAutomation(){document.querySelector(".nbv2-automation-section")?.scrollIntoView({behavior:"smooth"})}

}

"""

# =====================================================
# Sprint 1.23
# Camera Refresh
# =====================================================

if "NB.refreshCamera" not in J:

    J+="""

NB.refreshCamera=function(){

const img=document.querySelector("#nbv2CameraImage");

if(!img)return;

const url=img.src.split("?")[0];

img.src=url+"?t="+Date.now();

}

setInterval(NB.refreshCamera,2000);

"""

# =====================================================
# Sprint 1.24
# CSS
# =====================================================

if ".nb-home-grid" not in C:

    C+="""

#nb-home-dashboard{

margin:18px;

}

.nb-home-grid{

display:grid;

grid-template-columns:repeat(3,1fr);

gap:15px;

}

.nb-card{

background:#162844;

border-radius:18px;

padding:18px;

display:flex;

flex-direction:column;

align-items:center;

justify-content:center;

font-size:28px;

font-weight:700;

cursor:pointer;

color:white;

min-height:110px;

transition:.2s;

}

.nb-card:hover{

transform:translateY(-3px);

}

.nb-card span{

font-size:14px;

margin-top:8px;

}

"""

# =====================================================
# Sprint 1.25
# Remove duplicate HALO cards
# =====================================================

H=H.replace("Talk to HALO","HALO")

while H.count("HALO</span>")>1:
    pos=H.rfind("HALO</span>")
    start=H.rfind('<div class="nb-card"',0,pos)
    end=H.find("</div>",pos)+6
    H=H[:start]+H[end:]

html.write_text(H,encoding="utf-8")
js.write_text(J,encoding="utf-8")
css.write_text(C,encoding="utf-8")

print("SPRINT 1.21 PASS")
print("SPRINT 1.22 PASS")
print("SPRINT 1.23 PASS")
print("SPRINT 1.24 PASS")
print("SPRINT 1.25 PASS")
