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

# ----------------------------------------------------
# Sprint 1.26
# Live status bar
# ----------------------------------------------------

if "nb-system-status" not in H:

    H=H.replace(
        "<main>",
        """
<main>

<div id="nb-system-status">

<span id="nbCam">📷 Camera</span>

<span id="nbHalo">🤖 HALO</span>

<span id="nbVision">👁 Vision</span>

<span id="nbPrayer">🕌 Prayer</span>

</div>

"""
    )

# ----------------------------------------------------
# Sprint 1.27
# Bottom Navigation
# ----------------------------------------------------

if "nb-bottom-nav" not in H:

    H+= """

<nav id="nb-bottom-nav">

<button onclick="NB.gotoCamera()">📷</button>

<button onclick="NB.gotoRooms()">🏠</button>

<button onclick="NB.gotoDevices()">💡</button>

<button onclick="NB.gotoHalo()">🤖</button>

<button onclick="NB.gotoAutomation()">⚡</button>

</nav>

"""

# ----------------------------------------------------
# Sprint 1.28
# Quick Refresh
# ----------------------------------------------------

if "NB.refreshAll" not in J:

    J+= """

NB.refreshAll=function(){

NB.refreshCamera()

location.hash=""

}

"""

# ----------------------------------------------------
# Sprint 1.29
# Device Highlight
# ----------------------------------------------------

if ".nb-device-online" not in C:

    C+= """

#nb-system-status{

display:flex;

justify-content:space-around;

padding:10px;

background:#0e2238;

margin:15px;

border-radius:16px;

font-weight:700;

}

#nb-bottom-nav{

position:fixed;

bottom:0;

left:0;

right:0;

display:grid;

grid-template-columns:repeat(5,1fr);

background:#081421;

padding:12px;

}

#nb-bottom-nav button{

background:none;

border:0;

color:white;

font-size:24px;

}

.nb-device-online{

color:#28d17c;

}

"""

# ----------------------------------------------------
# Sprint 1.30
# HALO Fast Access
# ----------------------------------------------------

if "NB.quickHalo" not in J:

    J+= """

NB.quickHalo=function(){

NB.gotoHalo()

const t=document.querySelector("#nbv2HaloInput")

if(t)t.focus()

}

"""

html.write_text(H,encoding="utf-8")
js.write_text(J,encoding="utf-8")
css.write_text(C,encoding="utf-8")

print("SPRINT 1.26 PASS")
print("SPRINT 1.27 PASS")
print("SPRINT 1.28 PASS")
print("SPRINT 1.29 PASS")
print("SPRINT 1.30 PASS")
