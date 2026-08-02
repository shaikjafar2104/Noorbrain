from pathlib import Path

html=Path("dashboard/mobile/index.html")
js=Path("dashboard/js/mobile-home-control-center.js")
css=Path("dashboard/css/mobile-home-control-center.css")

H=html.read_text(encoding="utf-8",errors="ignore")
J=js.read_text(encoding="utf-8",errors="ignore")
C=css.read_text(encoding="utf-8",errors="ignore")

# remove second HALO orb
H=H.replace(
'<button id="nbv2HaloButton" class="nbv2-halo-orb" aria-label="Talk to HALO">✦</button>',
''
)

# add control center
if 'id="nbControlCenter"' not in H:
    block="""
<section id="nbControlCenter">

<button onclick="location.href='#nbv2CameraHero'">📷 Camera</button>

<button onclick="location.href='#nbv2Halo'">🤖 HALO</button>

<button onclick="location.href='#nbv2DeviceGrid'">💡 Devices</button>

<button onclick="location.href='#nb-room-grid'">🏠 Rooms</button>

<button onclick="location.href='#nbv2Install'">📱 Install</button>

<button onclick="location.href='/studio'">⚙ Studio</button>

</section>
"""
    H=H.replace("</main>",block+"\n</main>")

if "#nbControlCenter" not in C:
    C += """

#nbControlCenter{
display:grid;
grid-template-columns:repeat(3,1fr);
gap:12px;
margin:18px;
}

#nbControlCenter button{
height:74px;
border:0;
border-radius:18px;
font-weight:700;
cursor:pointer;
}

"""

if "window.NoorBrainQuickRefresh" not in J:
    J += """

window.NoorBrainQuickRefresh=function(){
if(window.NoorBrainMobileV2?.loadDevices){
NoorBrainMobileV2.loadDevices();
}
if(window.NoorBrainMobileV2?.loadConfig){
NoorBrainMobileV2.loadConfig();
}
};

"""

html.write_text(H,encoding="utf-8")
js.write_text(J,encoding="utf-8")
css.write_text(C,encoding="utf-8")

print("SPRINT 1.47 PASS")
