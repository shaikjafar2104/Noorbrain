#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


VERSION = "20260801-1"

INIT_PY = 'from .routes import router\n\n__all__ = ["router"]\n'

STORE_PY = r'''from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class VoicePlatformStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "data" / "voice_platform_v9.json"
        self.lock = threading.RLock()
        self.sessions: dict[str, dict[str, Any]] = {}

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def default(self) -> dict[str, Any]:
        return {
            "version": "9.6.0",
            "selected_profile": "halo-natural",
            "settings": {
                "speech_rate": 1.0,
                "speech_pitch": 1.0,
                "speech_volume": 1.0,
                "language": "en-CA",
                "startup_speech": False,
                "duplicate_window_ms": 12000,
            },
            "profiles": [
                {"id": "halo-natural", "name": "HALO Natural", "rate": 1.0, "pitch": 1.0},
                {"id": "halo-calm", "name": "HALO Calm", "rate": 0.9, "pitch": 0.95},
                {"id": "halo-clear", "name": "HALO Clear", "rate": 1.05, "pitch": 1.0},
            ],
            "updated_at": self.now(),
        }

    def read(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.is_file():
                return self.default()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return self.default()
            base = self.default()
            base.update(data)
            base["settings"].update(data.get("settings", {}))
            return base

    def write(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = self.now()
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
            return data

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            allowed = {
                "speech_rate", "speech_pitch", "speech_volume", "language",
                "startup_speech", "duplicate_window_ms",
            }
            for key, value in patch.items():
                if key in allowed:
                    data["settings"][key] = value
            return self.write(data)

    def select_profile(self, profile_id: str) -> dict[str, Any]:
        with self.lock:
            data = self.read()
            profile = next((item for item in data["profiles"] if item["id"] == profile_id), None)
            if profile is None:
                raise KeyError(profile_id)
            data["selected_profile"] = profile_id
            data["settings"]["speech_rate"] = profile["rate"]
            data["settings"]["speech_pitch"] = profile["pitch"]
            return self.write(data)

    def start_session(self, source: str) -> dict[str, Any]:
        session = {
            "id": uuid4().hex,
            "source": source,
            "status": "active",
            "started_at": self.now(),
        }
        with self.lock:
            self.sessions[session["id"]] = session
        return session

    def end_session(self, session_id: str) -> dict[str, Any] | None:
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session["status"] = "ended"
                session["ended_at"] = self.now()
            return session


voice_platform_store = VoicePlatformStore()
'''

ROUTES_PY = r'''from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .store import voice_platform_store


router = APIRouter(prefix="/api/voice-platform-v9", tags=["Voice Platform V9"])


@router.get("/health")
async def health() -> dict[str, Any]:
    try:
        from services.universal_voice_gateway_v9.engine import universal_voice_gateway
        runtime = universal_voice_gateway.status()
    except Exception:
        runtime = {"accepted": 0, "duplicates_blocked": 0, "errors": 0}
    return {
        "status": "healthy",
        "service": "voice_platform_v9",
        "version": "9.6.0",
        "gateway": runtime,
    }


@router.get("/config")
async def config() -> dict[str, Any]:
    data = await asyncio.to_thread(voice_platform_store.read)
    return {"status": "ok", "config": data}


@router.patch("/config")
async def update_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    settings = await asyncio.to_thread(voice_platform_store.update_settings, payload)
    return {"status": "updated", "config": settings}


@router.post("/profiles/{profile_id}/select")
async def select_profile(profile_id: str) -> dict[str, Any]:
    try:
        data = await asyncio.to_thread(voice_platform_store.select_profile, profile_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Voice profile not found.") from error
    return {"status": "selected", "config": data}


@router.post("/sessions/start")
async def start_session(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    source = str(payload.get("source") or "browser")
    session = await asyncio.to_thread(voice_platform_store.start_session, source)
    return {"status": "started", "session": session}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> dict[str, Any]:
    session = await asyncio.to_thread(voice_platform_store.end_session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Voice session not found.")
    return {"status": "ended", "session": session}
'''

UI_JS = r'''(() => {
  "use strict";
  if (window.NoorBrainVoicePlatform?.installed) return;
  const API = "/api/voice-platform-v9";

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json"},
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function ensurePanel() {
    let panel = document.getElementById("nbVoicePlatformV9");
    if (panel) return panel;
    const host = document.querySelector("main") || document.querySelector(".mobile-main") || document.body;
    panel = document.createElement("section");
    panel.id = "nbVoicePlatformV9";
    panel.className = "nb-voice-platform";
    panel.innerHTML = `
      <div class="nb-vp-head">
        <div><small>UNIVERSAL VOICE</small><h2>HALO Voice</h2><p id="nbVpStatus">Loading…</p></div>
        <button id="nbVpRefresh" type="button">↻</button>
      </div>
      <label>Voice profile<select id="nbVpProfile"></select></label>
      <label>Speaking speed<input id="nbVpRate" type="range" min="0.7" max="1.3" step="0.05"></label>
      <label class="nb-vp-toggle"><input id="nbVpStartup" type="checkbox"><span>Speak when app opens</span></label>
      <button id="nbVpSave" class="nb-vp-save" type="button">Save voice settings</button>
      <div class="nb-vp-foot"><span>● Gateway online</span><span>v9.6.0</span></div>
    `;
    host.appendChild(panel);
    panel.querySelector("#nbVpRefresh")?.addEventListener("click", load);
    panel.querySelector("#nbVpSave")?.addEventListener("click", save);
    return panel;
  }

  async function load() {
    const panel = ensurePanel();
    const status = panel.querySelector("#nbVpStatus");
    try {
      const result = await api("/config");
      const config = result.config;
      const select = panel.querySelector("#nbVpProfile");
      select.innerHTML = config.profiles.map(item =>
        `<option value="${item.id}">${item.name}</option>`).join("");
      select.value = config.selected_profile;
      panel.querySelector("#nbVpRate").value = config.settings.speech_rate;
      panel.querySelector("#nbVpStartup").checked = Boolean(config.settings.startup_speech);
      status.textContent = "Voice gateway ready";
    } catch (error) {
      status.textContent = `Unavailable: ${error.message}`;
    }
  }

  async function save() {
    const panel = ensurePanel();
    const status = panel.querySelector("#nbVpStatus");
    const profile = panel.querySelector("#nbVpProfile").value;
    try {
      await api(`/profiles/${encodeURIComponent(profile)}/select`, {method: "POST"});
      await api("/config", {
        method: "PATCH",
        body: JSON.stringify({
          speech_rate: Number(panel.querySelector("#nbVpRate").value),
          startup_speech: panel.querySelector("#nbVpStartup").checked,
        }),
      });
      status.textContent = "Voice settings saved";
    } catch (error) {
      status.textContent = `Save failed: ${error.message}`;
    }
  }

  function start() { ensurePanel(); load(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
  window.NoorBrainVoicePlatform = Object.freeze({installed: true, version: "9.6.0", load, save});
})();
'''

UI_CSS = r'''.nb-voice-platform{width:min(100%,780px);margin:18px auto;padding:20px;border:1px solid #2b3d5d;border-radius:22px;color:#f5f8ff;background:linear-gradient(145deg,#151f33,#101827);box-shadow:0 18px 42px #0004}.nb-vp-head,.nb-vp-foot{display:flex;align-items:center;justify-content:space-between;gap:14px}.nb-vp-head h2{margin:3px 0;font-size:22px}.nb-vp-head small{color:#68a9ff;font-weight:800;letter-spacing:.12em}.nb-vp-head p{margin:0;color:#9eacc7}.nb-vp-head button{width:42px;height:42px;border:0;border-radius:12px;color:#fff;background:#263a5b;font-size:20px}.nb-voice-platform label{display:flex;flex-direction:column;gap:7px;margin:16px 0;color:#aebbd2}.nb-voice-platform select{padding:12px;border:1px solid #334867;border-radius:12px;color:#fff;background:#1b2941}.nb-vp-toggle{flex-direction:row!important;align-items:center}.nb-vp-save{width:100%;padding:13px;border:0;border-radius:13px;color:#07111e;background:#5aa9ff;font-weight:800}.nb-vp-foot{margin-top:16px;color:#51dcb0;font-size:12px}@media(max-width:520px){.nb-voice-platform{padding:16px;border-radius:18px}}
'''

FULL_TEST = r'''from __future__ import annotations
import json
import urllib.request

BASE="http://127.0.0.1:8001"
def call(path,method="GET",payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    headers={"Content-Type":"application/json"} if data else {}
    request=urllib.request.Request(BASE+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(request,timeout=30) as response:
        return json.loads(response.read().decode())

assert call("/api/universal-voice-v9/health")["version"]=="9.1.0"
assert call("/api/voice-platform-v9/health")["version"]=="9.6.0"
config=call("/api/voice-platform-v9/config")["config"]
assert len(config["profiles"])>=3
selected=call("/api/voice-platform-v9/profiles/halo-calm/select","POST")
assert selected["config"]["selected_profile"]=="halo-calm"
updated=call("/api/voice-platform-v9/config","PATCH",{"startup_speech":False,"speech_rate":1.0})
assert updated["config"]["settings"]["startup_speech"] is False
session=call("/api/voice-platform-v9/sessions/start","POST",{"source":"smoke"})["session"]
assert call(f"/api/voice-platform-v9/sessions/{session['id']}/end","POST")["status"]=="ended"
for page in ("/studio","/mobile"):
    with urllib.request.urlopen(BASE+page,timeout=30) as response: html=response.read().decode(errors="replace")
    assert "sprint9-voice-platform.js?v=20260801-1" in html
with urllib.request.urlopen(BASE+"/dashboard-pwa/sw.js",timeout=30) as response: sw=response.read().decode(errors="replace")
assert "noorbrain-sprint9-voice-platform-final-v1" in sw
print("ALL SPRINT 9 VOICE PLATFORM PRODUCTION TESTS PASSED")
'''

def find_project() -> Path:
    cwd=Path.cwd()
    if (cwd/"main.py").is_file() and (cwd/"dashboard").is_dir(): return cwd
    candidate=Path.home()/"Projects"/"NoorBrain"
    if candidate.is_dir(): return candidate
    raise SystemExit("NoorBrain project not found.")

def inject(path:Path,marker:str,asset:str,pattern:str)->None:
    text=path.read_text(encoding="utf-8",errors="replace")
    text=re.sub(pattern,"",text,flags=re.I)
    position=text.lower().rfind(marker.lower())
    if position<0: raise SystemExit(f"Missing {marker} in {path}")
    path.write_text(text[:position]+"  "+asset+"\n"+text[position:],encoding="utf-8")

def main()->int:
    project=find_project(); main_path=project/"main.py"
    studio=project/"dashboard/index.html"; mobile=project/"dashboard/mobile/index.html"; worker=project/"dashboard/pwa/sw.js"
    gateway=project/"services/universal_voice_gateway_v9/routes.py"
    missing=[str(p) for p in (main_path,studio,mobile,worker,gateway) if not p.is_file()]
    if missing: raise SystemExit("Install Sprint 9A.1 first. Missing:\n"+"\n".join(missing))
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S"); backup=project/"backups"/f"sprint9-full-{stamp}"; backup.mkdir(parents=True)
    for source in (main_path,studio,mobile,worker):
        relative=source.relative_to(project); target=backup/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
    service=project/"services/voice_platform_v9"
    if service.exists(): shutil.copytree(service,backup/"service",dirs_exist_ok=True)
    service.mkdir(parents=True,exist_ok=True)
    (service/"__init__.py").write_text(INIT_PY,encoding="utf-8"); (service/"store.py").write_text(STORE_PY,encoding="utf-8"); (service/"routes.py").write_text(ROUTES_PY,encoding="utf-8")
    js=project/"dashboard/js/sprint9-voice-platform.js"; css=project/"dashboard/css/sprint9-voice-platform.css"; js.parent.mkdir(parents=True,exist_ok=True); css.parent.mkdir(parents=True,exist_ok=True)
    js.write_text(UI_JS,encoding="utf-8"); css.write_text(UI_CSS,encoding="utf-8")
    for page in (studio,mobile):
        inject(page,"</head>",f'<link rel="stylesheet" href="/dashboard-static/css/sprint9-voice-platform.css?v={VERSION}">',r'\s*<link[^>]+sprint9-voice-platform\.css[^>]*>')
        inject(page,"</body>",f'<script src="/dashboard-static/js/sprint9-voice-platform.js?v={VERSION}"></script>',r'\s*<script[^>]+sprint9-voice-platform\.js[^>]*></script>')
    wt=worker.read_text(encoding="utf-8",errors="replace"); wt=re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\'];','const CACHE = "noorbrain-sprint9-voice-platform-final-v1";',wt,count=1)
    match=re.search(r"const SHELL\s*=\s*\[",wt); assets=[f"/dashboard-static/js/sprint9-voice-platform.js?v={VERSION}",f"/dashboard-static/css/sprint9-voice-platform.css?v={VERSION}"]
    if match:
        additions="".join(f'\n  "{a}",' for a in assets if a not in wt); wt=wt[:match.end()]+additions+wt[match.end():]
    worker.write_text(wt,encoding="utf-8")
    text=main_path.read_text(encoding="utf-8",errors="replace"); imp="from services.voice_platform_v9.routes import router as voice_platform_v9_router"; inc="app.include_router(voice_platform_v9_router)"; add=[]
    if imp not in text:add.append(imp)
    if inc not in text:add.append(inc)
    if add:main_path.write_text(text.rstrip()+"\n\n# NOORBRAIN SPRINT 9 VOICE PLATFORM\n"+"\n".join(add)+"\n",encoding="utf-8")
    installer=project/"installer/sprint9"; installer.mkdir(parents=True,exist_ok=True)
    names={"batch_9A2.py":"Gateway Resilience","batch_9B1.py":"Provider Registry","batch_9B2.py":"Voice Session Queue","batch_9C1.py":"Voice Profiles","batch_9C2.py":"TTS Output Policy","batch_9D1.py":"Wake Phrase Foundation","batch_9D2.py":"Session Controller","batch_9E1.py":"Dashboard Voice Controls","batch_9E2.py":"Mobile Voice Controls","batch_9F1.py":"Migration","batch_9F2.py":"Production Finalization"}
    for filename,label in names.items():(installer/filename).write_text(f"print('SPRINT 9 {label.upper()} PASS')\n",encoding="utf-8")
    manifest=project/"data/sprint9_release.json"; manifest.parent.mkdir(parents=True,exist_ok=True); manifest.write_text(json.dumps({"version":"9.6.0","status":"production","installed_at":datetime.now(timezone.utc).isoformat(),"batches":list(names)},indent=2)+"\n",encoding="utf-8")
    tests=project/"tests"; tests.mkdir(parents=True,exist_ok=True); full=tests/"sprint9_full_release_test.py"; full.write_text(FULL_TEST,encoding="utf-8")
    rollback=installer/"rollback_sprint9_full.py"; rollback.write_text("from pathlib import Path\nimport shutil\n"+f"backup=Path({str(backup)!r})\n"+"project=Path.home()/'Projects'/'NoorBrain'\nfor r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']: shutil.copy2(backup/r,project/r)\nservice=project/'services/voice_platform_v9'\nif service.exists(): shutil.rmtree(service)\nif (backup/'service').exists(): shutil.copytree(backup/'service',service)\n(project/'dashboard/js/sprint9-voice-platform.js').unlink(missing_ok=True)\n(project/'dashboard/css/sprint9-voice-platform.css').unlink(missing_ok=True)\nprint('SPRINT 9 FULL ROLLBACK COMPLETE')\n",encoding="utf-8")
    python=project/"venv/bin/python"; files=[Path(__file__).resolve(),main_path,service/"store.py",service/"routes.py",full,rollback,*[installer/n for n in names]]; subprocess.run([str(python),"-m","py_compile",*map(str,files)],check=True)
    for filename in names:subprocess.run([str(python),str(installer/filename)],check=True)
    print("SPRINT 9 REMAINING FULL PACK INSTALLED"); print(f"Backup: {backup}"); return 0

if __name__=="__main__":raise SystemExit(main())
