from __future__ import annotations
import base64,shutil,subprocess,tempfile
from pathlib import Path
from fastapi import APIRouter,Body,FastAPI,HTTPException
app=FastAPI(title="NoorBrain Pi Audio Node",version="15.1.0");router=APIRouter(prefix="/api/pi-audio")
def command(name):
 path=shutil.which(name)
 if not path:raise RuntimeError(f"{name} not installed")
 return path
@app.get("/health")
def health():return {"status":"healthy","service":"noorbrain_pi_audio","version":"15.1.0","arecord":bool(shutil.which("arecord")),"aplay":bool(shutil.which("aplay"))}
@app.post("/play")
def play(payload:dict=Body(...)):
 try:data=base64.b64decode(str(payload.get("audio_base64") or ""),validate=True)
 except Exception as e:raise HTTPException(422,"Invalid audio") from e
 fmt=str(payload.get("format") or "wav").lower();suffix="."+(fmt if fmt in ("wav","mp3","ogg") else "wav")
 with tempfile.NamedTemporaryFile(suffix=suffix) as f:
  f.write(data);f.flush()
  if suffix==".wav":subprocess.run([command("aplay"),"-q",f.name],check=True,timeout=120)
  else:subprocess.run([command("ffplay"),"-nodisp","-autoexit","-loglevel","quiet",f.name],check=True,timeout=120)
 return {"status":"played","bytes":len(data)}
@app.post("/record")
def record(payload:dict=Body(default={})):
 seconds=max(1,min(int(payload.get("seconds",4)),15))
 with tempfile.NamedTemporaryFile(suffix=".wav") as f:
  subprocess.run([command("arecord"),"-q","-D","default","-f","S16_LE","-r","16000","-c","1","-d",str(seconds),f.name],check=True,timeout=seconds+10)
  data=Path(f.name).read_bytes()
 return {"status":"captured","format":"wav","seconds":seconds,"audio_base64":base64.b64encode(data).decode()}
app.include_router(router)
if __name__=="__main__":
 import uvicorn;uvicorn.run(app,host="0.0.0.0",port=8010)
