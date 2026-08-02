from pathlib import Path

mobile = Path("dashboard/mobile/index.html")
js = Path("dashboard/js/mobile-v2.js")
css = Path("dashboard/css/mobile-v2.css")

html = mobile.read_text(encoding="utf-8")
code = js.read_text(encoding="utf-8")
style = css.read_text(encoding="utf-8")

# Remove duplicate HALO button
html = html.replace(
    '<button id="nbv2HaloButton" class="nbv2-halo-orb" aria-label="Talk to HALO">✦</button>',
    ''
)

# Add camera status badge
if "nbv2CameraStatus" not in html:
    html = html.replace(
        '<div id="nbv2CameraHero" class="nbv2-camera-hero">',
        '<div class="nbv2-camera-status" id="nbv2CameraStatus">LIVE</div>\n'
        '<div id="nbv2CameraHero" class="nbv2-camera-hero">'
    )

# Camera auto-refresh
if "setInterval(() => {" not in code:
    code += """

setInterval(() => {
    if(state.activeCamera){
        showCamera(state.activeCamera);
    }
},3000);

"""

# Button fix
if "pointer-events:auto" not in style:
    style += """

button{
pointer-events:auto!important;
touch-action:manipulation!important;
}

.nbv2-nav button{
pointer-events:auto!important;
}

.nbv2-camera-status{
display:inline-block;
padding:6px 12px;
border-radius:999px;
background:#1fa463;
color:white;
font-weight:700;
margin-bottom:10px;
}

"""

mobile.write_text(html,encoding="utf-8")
js.write_text(code,encoding="utf-8")
css.write_text(style,encoding="utf-8")

print("SPRINT 1.14 APPLIED")
