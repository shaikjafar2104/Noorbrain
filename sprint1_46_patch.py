from pathlib import Path

HTML=Path("dashboard/mobile/index.html")
JS=Path("dashboard/js/mobile-home-control-center.js")
CSS=Path("dashboard/css/mobile-home-control-center.css")

h=HTML.read_text(encoding="utf-8",errors="ignore")
j=JS.read_text(encoding="utf-8",errors="ignore")
c=CSS.read_text(encoding="utf-8",errors="ignore")

# ---------- Camera Quick Card ----------

if 'id="nb-quick-camera"' not in h:

    camera="""

<section id="nb-quick-camera" class="nb-home-card">

<div class="nb-card-header">
<h3>📷 Live Camera</h3>
<button onclick="NB.refreshCamera()">Refresh</button>
</div>

<img id="nbQuickCamera"
src="/video_feed"
style="width:100%;border-radius:16px;object-fit:cover;aspect-ratio:16/9;">

<div class="nb-camera-actions">

<button onclick="NB.cameraFullscreen()">Fullscreen</button>

<button onclick="NB.openCameraStudio()">Controls</button>

</div>

</section>

"""

    h=h.replace('<section class="nbv2-camera-section">',camera+'\n<section class="nbv2-camera-section">')

# ---------- JS ----------

if "NB.cameraFullscreen" not in j:

    j += """

window.NB=window.NB||{};

NB.refreshCamera=function(){

const img=document.getElementById("nbQuickCamera");

if(!img)return;

img.src="/video_feed?t="+Date.now();

};

NB.cameraFullscreen=function(){

const img=document.getElementById("nbQuickCamera");

if(img&&img.requestFullscreen){

img.requestFullscreen();

}

};

NB.openCameraStudio=function(){

window.location="/studio#vision";

};

setInterval(NB.refreshCamera,3000);

"""

# ---------- CSS ----------

if "#nb-quick-camera" not in c:

    c += """

#nb-quick-camera{

margin:18px;

padding:18px;

border-radius:20px;

background:#172b47;

}

.nb-card-header{

display:flex;

justify-content:space-between;

align-items:center;

margin-bottom:12px;

}

.nb-camera-actions{

display:flex;

gap:10px;

margin-top:12px;

}

.nb-camera-actions button,

.nb-card-header button{

border:0;

padding:10px 14px;

border-radius:12px;

cursor:pointer;

}

"""

HTML.write_text(h,encoding="utf-8")
JS.write_text(j,encoding="utf-8")
CSS.write_text(c,encoding="utf-8")

print("SPRINT 1.46 PASS")
