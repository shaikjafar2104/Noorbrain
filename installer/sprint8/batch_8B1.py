from pathlib import Path
import subprocess

P = Path.home() / "Projects" / "NoorBrain"
main = P / "main.py"
mobile = P / "dashboard" / "mobile" / "index.html"

text = main.read_text(encoding="utf-8", errors="replace")

imp = (
    "from services.routine_intelligence_v8.routes "
    "import router as routine_intelligence_v8_router"
)
inc = "app.include_router(routine_intelligence_v8_router)"

if imp not in text:
    text += (
        "\n\n# NOORBRAIN SPRINT 8B ROUTINE INTELLIGENCE\n"
        + imp
        + "\n"
    )

if inc not in text:
    text += inc + "\n"

main.write_text(text, encoding="utf-8")

html = mobile.read_text(encoding="utf-8", errors="replace")

css = (
    '<link rel="stylesheet" '
    'href="/dashboard-static/css/'
    'sprint8b-routine-intelligence.css?v=20260731-1">'
)
js = (
    '<script src="/dashboard-static/js/'
    'sprint8b-routine-intelligence.js?v=20260731-1"></script>'
)

if css not in html:
    html = html.replace("</head>", "  " + css + "\n</head>")

if js not in html:
    html = html.replace("</body>", "  " + js + "\n</body>")

mobile.write_text(html, encoding="utf-8")

subprocess.run(
    [
        str(P / "venv" / "bin" / "python"),
        "-m",
        "py_compile",
        str(P / "main.py"),
    ],
    check=True,
)

print("SPRINT 8B.1 TIMELINE CORE PASS")
