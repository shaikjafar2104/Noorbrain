(() => {
  "use strict";

  const API = "/api/mobile-v2";
  const state = {cameras:[],activeCamera:null,devices:[],installPrompt:null,recorder:null,stream:null,chunks:[],recording:false};

  async function request(path, options={}) {
    const response = await fetch(path,{headers:{"Content-Type":"application/json","Accept":"application/json"},cache:"no-store",...options});
    const payload = await response.json().catch(()=>({}));
    if(!response.ok) throw new Error(payload.detail || payload.message || `HTTP ${response.status}`);
    return payload;
  }

  const esc = value => String(value ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const bust = url => `${url}${url.includes("?")?"&":"?"}v=${Date.now()}`;

  function showCamera(camera) {
    state.activeCamera=camera;
    const hero=document.querySelector("#nbv2CameraHero");
    if(!camera){hero.innerHTML='<div class="nbv2-camera-empty"><span>📷</span><b>No camera configured</b><small>Tap Add to enter a stream URL.</small></div>';return;}
    hero.innerHTML=`<img id="nbv2CameraImage" src="${esc(bust(camera.stream_url))}" alt="${esc(camera.name)}">`;
    document.querySelector("#nbv2CameraImage").onerror=()=>{hero.innerHTML=`<div class="nbv2-camera-empty"><span>⚠️</span><b>${esc(camera.name)} unavailable</b><small>Check camera service and URL.</small></div>`;};
    renderCameraStrip();
  }

  function renderCameraStrip(){
    const strip=document.querySelector("#nbv2CameraStrip");
    strip.innerHTML=state.cameras.map(c=>`<button class="nbv2-camera-chip ${c.id===state.activeCamera?.id?"active":""}" data-camera="${esc(c.id)}">${esc(c.name)}</button>`).join("");
    strip.querySelectorAll("[data-camera]").forEach(b=>b.onclick=()=>showCamera(state.cameras.find(c=>c.id===b.dataset.camera)));
  }

  async function loadConfig(){
    try{const p=await request(`${API}/config`);state.cameras=p.config?.cameras||[];}
    catch(_){state.cameras=[{id:"fallback",name:"NoorBrain Camera",room:"Home",stream_url:"/video_feed"}];}
    showCamera(state.cameras[0]||null);
  }

  async function loadDevices(){
    const grid=document.querySelector("#nbv2DeviceGrid");
    try{const p=await request("/api/halo-oneclick/devices");state.devices=p.devices||[];}catch(_){state.devices=[];}
    if(!state.devices.length){grid.innerHTML='<button class="nbv2-device-empty" id="nbv2DeviceEmpty">＋ Add your first home device</button>';document.querySelector("#nbv2DeviceEmpty").onclick=addDevice;return;}
    grid.innerHTML=state.devices.map(d=>`<button class="nbv2-device-card ${d.state==="on"?"on":""}" data-device="${esc(d.id)}"><span>${d.type==="light"?"💡":"⌁"}</span><b>${esc(d.name)}</b><small>${esc(d.room||"Home")}</small><span class="nbv2-device-state">${d.state==="on"?"ON":"OFF"}</span></button>`).join("");
    grid.querySelectorAll("[data-device]").forEach(b=>b.onclick=async()=>{b.disabled=true;try{await request(`/api/halo-oneclick/devices/${b.dataset.device}/toggle`,{method:"POST",body:"{}"});await loadDevices();}finally{b.disabled=false;}});
  }

  function addDevice(){location.href="/studio#devices";}

  function addCameraModal(){
    const modal=document.querySelector("#nbv2Modal");modal.hidden=false;
    modal.innerHTML=`<form class="nbv2-modal-card" id="nbv2CameraForm"><h2>Add Camera</h2><label>Camera name<input name="name" required placeholder="Hall Camera"></label><label>Room<input name="room" value="Hall"></label><label>Stream URL<input name="stream_url" required placeholder="http://192.168.2.50:8000/video_feed"></label><div class="nbv2-modal-actions"><button type="button" id="nbv2ModalCancel">Cancel</button><button type="submit">Save</button></div></form>`;
    document.querySelector("#nbv2ModalCancel").onclick=()=>modal.hidden=true;
    document.querySelector("#nbv2CameraForm").onsubmit=async e=>{e.preventDefault();await request(`${API}/cameras`,{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target).entries()))});modal.hidden=true;await loadConfig();};
  }

  async function sendHalo(command){
    const reply=document.querySelector("#nbv2HaloReply"),input=document.querySelector("#nbv2HaloInput");
    const message=String(command||input.value||"").trim();if(!message)return;
    input.value="";reply.textContent="Thinking…";
    try{
      const p=await request("/api/halo-oneclick/command",{method:"POST",body:JSON.stringify({message})});
      if(p.status==="forward"){const h=await request("/halo",{method:"POST",body:JSON.stringify({message})});reply.textContent=h.reply||h.message||"Done.";}
      else reply.textContent=p.reply||"Done.";
      window.NoorBrainHALOSpeak?.(reply.textContent);
    }catch(e){reply.textContent=e.message;}
  }

  async function toggleMic(){
    if(state.recording){state.recorder.stop();return;}
    if(!window.isSecureContext){document.querySelector("#nbv2HaloReply").textContent="Microphone requires HTTPS or localhost.";return;}
    try{
      state.stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      const mime=["audio/webm;codecs=opus","audio/webm","audio/mp4"].find(t=>MediaRecorder.isTypeSupported(t));
      state.recorder=mime?new MediaRecorder(state.stream,{mimeType:mime}):new MediaRecorder(state.stream);
      state.chunks=[];state.recording=true;document.querySelector("#nbv2HaloMic").textContent="■ Stop";
      state.recorder.ondataavailable=e=>{if(e.data?.size)state.chunks.push(e.data);};
      state.recorder.onstop=async()=>{
        state.recording=false;state.stream.getTracks().forEach(t=>t.stop());document.querySelector("#nbv2HaloMic").textContent="🎤 Push to Talk";
        const form=new FormData();form.append("audio",new Blob(state.chunks,{type:state.recorder.mimeType||"audio/webm"}),"mobile.webm");
        const r=await fetch("/api/halo-voice/transcribe",{method:"POST",body:form});const p=await r.json().catch(()=>({}));
        if(!r.ok){document.querySelector("#nbv2HaloReply").textContent=p.detail||`Voice HTTP ${r.status}`;return;}
        await sendHalo(p.command||p.text);
      };
      state.recorder.start(250);document.querySelector("#nbv2HaloReply").textContent="Listening… tap Stop when finished.";
    }catch(e){document.querySelector("#nbv2HaloReply").textContent=e.message;}
  }

  const modules={
    devices:"/studio#devices",vision:"/studio#vision",zones:"/studio#vision-zones",presence:"/studio#person-presence",
    faces:"/studio#face-identity",prayer:"/studio#prayer-intelligence",reminders:"/studio#islamic-reminders",
    rules:"/studio#reminder-rules",automation:"/studio#smart-automation",habits:"/studio#habit-learning",
    insights:"/studio#ai-insights",family:"/studio#family",notifications:"/studio#notifications",
    media:"/studio#media-library",voice:"/studio#halo-speak",settings:"/studio"
  };

  async function checkStatus(){
    const checks={
      camera:["/api/mobile-v2/health","/health"],
      halo:["/api/halo-oneclick/health","/api/halo-brain/health"],
      vision:["/api/vision-intelligence/health","/api/vision/health"],
      prayer:["/api/prayer-intelligence/health","/api/prayer/health"]
    };
    for(const [name,urls] of Object.entries(checks)){
      let ok=false;
      for(const url of urls){try{const r=await fetch(url,{cache:"no-store"});if(r.ok){ok=true;break;}}catch(_){}}
      const node=document.querySelector(`[data-status="${name}"]`);node.textContent=ok?"Online":"Unavailable";node.dataset.state=ok?"ok":"bad";
    }
    document.querySelector("#nbv2SystemStatus").textContent="NoorBrain mobile control ready.";
  }

  function navigate(tab){
    const target={home:".nbv2-hero",devices:"#nbv2Devices",halo:"#nbv2Halo",camera:"#nbv2CameraSection",more:"#nbv2Modules"}[tab];
    document.querySelector(target)?.scrollIntoView({behavior:"smooth",block:"start"});
    document.querySelectorAll(".nbv2-nav button").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));
    document.querySelector("#nbv2PageTitle").textContent=tab[0].toUpperCase()+tab.slice(1);
  }

  function bind(){
    document.querySelector("#nbv2Refresh").onclick=()=>Promise.allSettled([loadConfig(),loadDevices(),checkStatus()]);
    document.querySelector("#nbv2AddCamera").onclick=addCameraModal;
    document.querySelector("#nbv2AddDevice").onclick=addDevice;
    document.querySelector("#nbv2HaloSend").onclick=()=>sendHalo();
    document.querySelector("#nbv2HaloMic").onclick=toggleMic;
    document.querySelector("#nbv2PrimaryHalo").onclick=()=>navigate("halo");
    document.querySelector("#nbv2HaloInput").onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendHalo();}};
    document.querySelector("#nbv2CameraRefresh").onclick=()=>showCamera(state.activeCamera);
    document.querySelector("#nbv2CameraFullscreen").onclick=async()=>{const h=document.querySelector("#nbv2CameraHero");document.fullscreenElement?await document.exitFullscreen():await h.requestFullscreen?.();};
    document.querySelector("#nbv2OpenVision").onclick=()=>location.href="/studio#vision";
    document.querySelectorAll("[data-module]").forEach(b=>b.onclick=()=>location.href=modules[b.dataset.module]||"/studio");
    document.querySelectorAll(".nbv2-nav button").forEach(b=>b.onclick=()=>navigate(b.dataset.tab));
    window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();state.installPrompt=e;});
    document.querySelector("#nbv2Install").onclick=async()=>{if(state.installPrompt){state.installPrompt.prompt();await state.installPrompt.userChoice;state.installPrompt=null;}else alert("Browser menu → Install App / Add to Home Screen");};
  }

  async function boot(){bind();await Promise.allSettled([loadConfig(),loadDevices(),checkStatus()]);}
  window.NoorBrainMobileV2={version:"1.50",loadConfig,loadDevices,sendHalo,checkStatus};
  document.readyState==="loading"?document.addEventListener("DOMContentLoaded",boot):boot();
})();
