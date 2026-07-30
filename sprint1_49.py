from pathlib import Path

HTML=Path("dashboard/mobile/index.html")
JS=Path("dashboard/js/mobile-home-control-center.js")
CSS=Path("dashboard/css/mobile-home-control-center.css")

h=HTML.read_text(encoding="utf-8",errors="ignore")
j=JS.read_text(encoding="utf-8",errors="ignore")
c=CSS.read_text(encoding="utf-8",errors="ignore")

# ---------- Quick Actions ----------

if 'id="nbQuickActions"' not in h:

    block="""
<section id="nbQuickActions">

<button onclick="window.location='/studio'">🏠 Dashboard</button>

<button onclick="window.location='/mobile'">📱 Mobile</button>

<button onclick="window.location='/video_feed'">📷 Camera</button>

<button onclick="NB.refreshCamera()">🔄 Refresh</button>

<button onclick="NB.quickHalo()">🤖 HALO</button>

<button onclick="window.location='/studio#devices'">💡 Devices</button>

<button onclick="window.location='/studio#vision'">👁 Vision</button>

<button onclick="window.location='/studio#automation'">⚡ Automation</button>

</section>
"""

    h=h.replace("</main>",block+"\n</main>")

# ---------- JS ----------

if "NB.quickHalo" not in j:

    j += """

window.NB=window.NB||{};

NB.quickHalo=function(){

const input=document.querySelector("#nbv2HaloInput");

if(input){

input.focus();

input.scrollIntoView({behavior:"smooth"});

}

};

"""

# ---------- CSS ----------

if "#nbQuickActions" not in c:

    c += """

#nbQuickActions{

display:grid;

grid-template-columns:repeat(4,1fr);

gap:12px;

margin:18px;

}

#nbQuickActions button{

height:70px;

border:0;

border-radius:16px;

background:#1c3558;

color:#fff;

font-weight:700;

cursor:pointer;

}

#nbQuickActions button:hover{

filter:brightness(1.08);

}

"""

HTML.write_text(h,encoding="utf-8")
JS.write_text(j,encoding="utf-8")
CSS.write_text(c,encoding="utf-8")

print("SPRINT 1.49 PASS")
