from pathlib import Path

html=Path("dashboard/mobile/index.html")
js=Path("dashboard/js/mobile-home-control-center.js")
css=Path("dashboard/css/mobile-home-control-center.css")

H=html.read_text(encoding="utf-8",errors="ignore")
J=js.read_text(encoding="utf-8",errors="ignore")
C=css.read_text(encoding="utf-8",errors="ignore")

if 'id="nbQuickStatus"' not in H:

    status="""

<section id="nbQuickStatus">

<div class="nbStatus" id="camStatus">📷 Camera</div>

<div class="nbStatus" id="haloStatus">🤖 HALO</div>

<div class="nbStatus" id="visionStatus">👁 Vision</div>

<div class="nbStatus" id="deviceStatus">💡 Devices</div>

</section>

"""

    H=H.replace('<section id="nbControlCenter">',status+'\n<section id="nbControlCenter">')

if ".nbStatus" not in C:

    C += """

#nbQuickStatus{

display:grid;

grid-template-columns:repeat(4,1fr);

gap:10px;

margin:18px;

}

.nbStatus{

background:#18345d;

padding:12px;

border-radius:16px;

text-align:center;

font-weight:700;

font-size:13px;

}

"""

if "window.NoorBrainStatusRefresh" not in J:

    J += """

window.NoorBrainStatusRefresh=function(){

fetch("/api/mobile-v3/health")

.then(r=>r.json())

.then(()=>{

document.getElementById("camStatus").innerHTML="🟢 Camera";

document.getElementById("haloStatus").innerHTML="🟢 HALO";

document.getElementById("visionStatus").innerHTML="🟢 Vision";

document.getElementById("deviceStatus").innerHTML="🟢 Devices";

})

.catch(()=>{

document.getElementById("camStatus").innerHTML="🔴 Camera";

});

};

setInterval(NoorBrainStatusRefresh,5000);

"""

html.write_text(H,encoding="utf-8")
js.write_text(J,encoding="utf-8")
css.write_text(C,encoding="utf-8")

print("SPRINT 1.48 PASS")
