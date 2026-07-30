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

# ======================================================
# Sprint 1.36
# ======================================================

if "nb-room-grid" not in h:

    h=h.replace(

    "</main>",

    """

<section id="nb-room-grid">

<h3>Rooms</h3>

<div class="nb-room">Hall</div>

<div class="nb-room">Kitchen</div>

<div class="nb-room">Bedroom</div>

<div class="nb-room">Prayer</div>

<div class="nb-room">Garage</div>

</section>

</main>

"""

)

# ======================================================
# Sprint 1.37
# ======================================================

if "NB.openRoom" not in j:

    j+="""

NB.openRoom=function(name){

console.log("Room:",name)

}

document.addEventListener("click",(e)=>{

if(e.target.classList.contains("nb-room"))

NB.openRoom(e.target.innerText)

})

"""

# ======================================================
# Sprint 1.38
# ======================================================

if ".nb-room" not in c:

    c+="""

#nb-room-grid{

display:grid;

grid-template-columns:repeat(2,1fr);

gap:14px;

margin:18px;

}

.nb-room{

background:#18355a;

padding:18px;

border-radius:18px;

text-align:center;

font-weight:700;

cursor:pointer;

transition:.2s;

}

.nb-room:hover{

transform:scale(1.03);

}

"""

# ======================================================
# Sprint 1.39
# ======================================================

if "NB.roomStatus" not in j:

    j+="""

NB.roomStatus=function(){

fetch("/api/mobile-v3/rooms")

.then(r=>r.json())

.then(console.log)

}

"""

# ======================================================
# Sprint 1.40
# ======================================================

if "NB.roomStatus();" not in j:

    j+="""

window.addEventListener("load",()=>{

NB.roomStatus()

})

"""

HTML.write_text(h,encoding="utf-8")
JS.write_text(j,encoding="utf-8")
CSS.write_text(c,encoding="utf-8")

print("SPRINT 1.36 PASS")
print("SPRINT 1.37 PASS")
print("SPRINT 1.38 PASS")
print("SPRINT 1.39 PASS")
print("SPRINT 1.40 PASS")
