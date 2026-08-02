from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/"data"/"mobile_v3"/"layout.json"

def layout():
    return json.loads(DATA.read_text())
