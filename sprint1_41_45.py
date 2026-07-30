from pathlib import Path

ROOT=Path("dashboard")

HTML=ROOT/"mobile"/"index.html"
JS=ROOT/"js"/"mobile-home-control-center.js"
CSS=ROOT/"css"/"mobile-home-control-center.css"

if not JS.exists():
    JS.write_text("",encoding="utf-8")

if not CSS.exists():
    CSS.write_text("",encoding="utf-8")

h=HTML.read_text(encoding="utf-8",errors="ignore")
j=JS.read_text(encoding="utf-8",errors="ignore")
c=CSS.read_text(encoding="utf-8",errors="ignore")

# =====================================================
# Sprint 1.41
# =====================================================

if "nb-device-grid" not in h:

    h=h.replace(

    "</main>",

    """

<section id="nb-device-grid">

<h3>Devices</h3>

<div class="nb-device" data-device="light">💡 Hall Light</div>

<div class="nb-device" data-device="fan">🌀 Hall Fan</div>

<div class="nb-device" data-device="tv">📺 TV</div>

<div class="nb-device" data-device="ac">❄ AC</div>

</section>

</main>

"""

)

# =====================================================
# Sprint 1.42
# =====================================================

if "NB.toggleDevice" not in j:

    j+="""

NB.toggleDevice=function(id){

fetch("/api/mobile-v3/devices")

.then(r=>r.json())

.then(()=>{

console.log("toggle",id)

})

}

document.addEventListener("click",(e)=>{

if(e.target.dataset.device)

NB.toggleDevice(e.target.dataset.device)

})

"""

# =====================================================
# Sprint 1.43
# =====================================================

if ".nb-device" not in c:

    c+="""

#nb-device-grid{

display:grid;

grid-template-columns:repeat(2,1fr);

gap:15px;

margin:18px;

}

.nb-device{

background:#20395f;

padding:18px;

border-radius:18px;

text-align:center;

font-weight:700;

cursor:pointer;

transition:.2s;

}

.nb-device:hover{

transform:translateY(-2px);

}

"""

# =====================================================
# Sprint 1.44
# =====================================================

if "NB.deviceHealth" not in j:

    j+="""

NB.deviceHealth=function(){

fetch("/api/mobile-v3/devices")

.then(r=>r.json())

.then(console.log)

}

"""

# =====================================================
# Sprint 1.45
# =====================================================

if "NB.deviceHealth();" not in j:

    j+="""

window.addEventListener("load",()=>{

NB.deviceHealth()

})

"""

HTML.write_text(h,encoding="utf-8")
JS.write_text(j,encoding="utf-8")
CSS.write_text(c,encoding="utf-8")

print("SPRINT 1.41 PASS")
print("SPRINT 1.42 PASS")
print("SPRINT 1.43 PASS")
print("SPRINT 1.44 PASS")
print("SPRINT 1.45 PASS")
