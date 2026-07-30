(() => {
  "use strict";
  const VERSION = "1.0.0";
  const $ = (s, root = document) => root.querySelector(s);
  const all = (s, root = document) => [...root.querySelectorAll(s)];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const safeText = value => String(value ?? "");

  async function api(path, options = {}) {
    const response = await fetch(path, {cache:"no-store", headers:{"Content-Type":"application/json", ...(options.headers||{})}, ...options});
    const type = response.headers.get("content-type") || "";
    const body = type.includes("json") ? await response.json() : {text: await response.text()};
    if (!response.ok) throw new Error(body.detail || body.message || `HTTP ${response.status}`);
    return body;
  }

  function toast(message, kind = "ok") {
    let el = $("#nbPremiumToast");
    if (!el) {
      el = document.createElement("div");
      el.id = "nbPremiumToast";
      Object.assign(el.style,{position:"fixed",right:"18px",bottom:"18px",zIndex:"1000000",padding:"13px 16px",borderRadius:"14px",background:"#14243a",color:"#fff",boxShadow:"0 18px 50px rgba(0,0,0,.35)",maxWidth:"360px",transition:".2s ease"});
      document.body.appendChild(el);
    }
    el.style.border = `1px solid ${kind === "error" ? "rgba(255,123,143,.5)" : "rgba(78,224,161,.45)"}`;
    el.textContent = message;
    el.style.opacity = "1";
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.style.opacity = "0", 3200);
  }

  function openPage(page) {
    const target = $(`[data-page="${page}"]`);
    if (target) target.click();
    else if (page === "halo") $("#haloInput,#haloText")?.focus();
  }

  function createHome() {
    const dashboard = $("#page-dashboard");
    if (!dashboard || $("#nbPremiumHome")) return;
    const wrap = document.createElement("div");
    wrap.id = "nbPremiumHome";
    wrap.className = "nb-premium-home";
    wrap.innerHTML = `
      <section class="nb-hero">
        <div>
          <div class="nb-eyebrow">NOORBRAIN HOME</div>
          <h2>Assalamu Alaikum.<br>Your home is ready.</h2>
          <p>Talk to HALO, check your rooms, manage reminders, and control NoorBrain from one simple place.</p>
          <div class="nb-hero-actions">
            <button class="button nb-primary" data-nb-action="talk">🎙 Talk to HALO</button>
            <button class="button nb-soft" data-nb-page="halo">💬 Open Chat</button>
            <button class="button nb-soft" data-nb-page="smart-automation">⚡ Automations</button>
          </div>
        </div>
        <div class="nb-orb-wrap"><div><div class="nb-orb" id="nbHaloOrb"></div><div class="nb-orb-label" id="nbHaloOrbLabel">HALO is ready</div></div></div>
      </section>
      <div class="nb-section-title"><div><h3>Quick actions</h3><p>Everything you use most.</p></div></div>
      <section class="nb-quick-grid">
        <div class="nb-quick-card" data-nb-page="prayer-intelligence"><span class="nb-quick-icon">🕌</span><strong>Prayer</strong><small>Times, alerts and guidance</small></div>
        <div class="nb-quick-card" data-nb-page="islamic-reminders"><span class="nb-quick-icon">🤲</span><strong>Reminders</strong><small>Duas, Azkar and routines</small></div>
        <div class="nb-quick-card" data-nb-page="gallery"><span class="nb-quick-icon">👨‍👩‍👧‍👦</span><strong>Family</strong><small>Face identity and presence</small></div>
        <div class="nb-quick-card" data-nb-page="smart-automation"><span class="nb-quick-icon">✨</span><strong>Automations</strong><small>Simple smart routines</small></div>
      </section>
      <div class="nb-section-title"><div><h3>Your home</h3><p>Room-first control inspired by modern smart homes.</p></div><button class="button nb-soft" data-nb-page="devices">View devices</button></div>
      <section class="nb-room-grid">
        <div class="nb-room-card" data-nb-page="presence"><div class="nb-room-head"><span>🛋️</span><span class="nb-room-dot"></span></div><strong>Hall</strong><small id="nbHallState">Checking presence…</small></div>
        <div class="nb-room-card" data-nb-page="vision"><div class="nb-room-head"><span>📷</span><span class="nb-room-dot"></span></div><strong>Camera</strong><small id="nbCameraState">Checking vision…</small></div>
        <div class="nb-room-card" data-nb-page="halo"><div class="nb-room-head"><span>🔊</span><span class="nb-room-dot"></span></div><strong>HALO Speak</strong><small id="nbVoiceState">Checking voice…</small></div>
        <div class="nb-room-card" data-nb-page="mobile-notifications"><div class="nb-room-head"><span>📱</span><span class="nb-room-dot"></span></div><strong>Mobile</strong><small id="nbMobileState">Checking notifications…</small></div>
      </section>`;
    dashboard.prepend(wrap);
    all("[data-nb-page]", wrap).forEach(el => el.addEventListener("click", () => openPage(el.dataset.nbPage)));
    $("[data-nb-action='talk']", wrap)?.addEventListener("click", openMicSheet);
    refreshHome();
  }

  async function refreshHome() {
    const jobs = [
      ["/api/halo-voice-runtime/status", "#nbVoiceState", d => `Voice ${d.status || "ready"}`],
      ["/api/ui-recovery/mobile/status", "#nbMobileState", d => `${d.summary?.unread ?? 0} unread notifications`],
      ["/api/vision/status", "#nbCameraState", d => `Vision ${d.status || d.state || "online"}`],
      ["/api/person-presence/status", "#nbHallState", d => `${d.present_count ?? d.count ?? 0} present now`]
    ];
    await Promise.allSettled(jobs.map(async ([path, selector, format]) => {
      try { const data = await api(path); const el = $(selector); if (el) el.textContent = format(data); } catch (_) {}
    }));
  }

  function micMarkup() {
    return `<div class="nb-mic-sheet" id="nbMicSheet" role="dialog" aria-modal="true">
      <div class="nb-mic-panel">
        <h3>Talk to HALO</h3><p>Tap the microphone, speak naturally, then HALO will send your request.</p>
        <button class="nb-mic-button" id="nbMicButton" aria-label="Start microphone">🎙️</button>
        <div class="nb-mic-status" id="nbMicStatus">Ready</div>
        <textarea id="nbMicTranscript" rows="3" placeholder="Your words will appear here…" style="width:100%;margin-top:14px;border-radius:16px;border:1px solid rgba(255,255,255,.1);background:#07111f;color:#fff;padding:13px"></textarea>
        <div class="nb-sheet-actions"><button class="button nb-primary" id="nbMicSend">Send to HALO</button><button class="button nb-soft" id="nbMicClose">Close</button></div>
      </div></div>`;
  }

  let recognition = null;
  let stream = null;
  let recorder = null;

  function closeMicSheet() {
    recognition?.stop?.(); recorder?.stop?.(); stream?.getTracks?.().forEach(t => t.stop());
    $("#nbMicSheet")?.remove(); $("#nbHaloOrb")?.classList.remove("listening");
  }

  async function sendTranscript() {
    const text = $("#nbMicTranscript")?.value?.trim();
    if (!text) return toast("Please speak or type a message first.", "error");
    const status = $("#nbMicStatus");
    try {
      status.textContent = "HALO is thinking…";
      const result = await api("/api/halo-conversation/chat", {method:"POST", body:JSON.stringify({text, session_id:"premium-ui", confirm:false})});
      status.textContent = result.reply || "HALO completed your request.";
      const haloInput = $("#haloInput") || $("#haloText"); if (haloInput) haloInput.value = text;
      toast("HALO replied successfully.");
    } catch (error) { status.textContent = `HALO error: ${error.message}`; toast(status.textContent,"error"); }
  }

  async function fallbackRecorder(button, status) {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Microphone requires HTTPS or localhost.");
    stream = await navigator.mediaDevices.getUserMedia({audio:true});
    status.textContent = "Microphone permission granted. Browser speech transcription is unavailable; type your request or use Chrome/Edge for live transcription.";
    button.classList.add("is-live"); button.textContent = "■";
    if (window.MediaRecorder) {
      const chunks = [];
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = e => e.data.size && chunks.push(e.data);
      recorder.onstop = () => { stream?.getTracks().forEach(t=>t.stop()); button.classList.remove("is-live"); button.textContent="🎙️"; status.textContent = "Microphone works. Audio captured locally; transcription is not supported by this browser."; };
      recorder.start(); await sleep(4500); if (recorder.state === "recording") recorder.stop();
    }
  }

  async function startMic() {
    const button = $("#nbMicButton"), status = $("#nbMicStatus"), transcript = $("#nbMicTranscript");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { try { await fallbackRecorder(button,status); } catch(e){ status.textContent=e.message; toast(e.message,"error"); } return; }
    recognition = new SR(); recognition.continuous=false; recognition.interimResults=true; recognition.lang=navigator.language || "en-US";
    recognition.onstart=()=>{button.classList.add("is-live");button.textContent="◼";status.textContent="Listening…";$("#nbHaloOrb")?.classList.add("listening")};
    recognition.onresult=e=>{let final="", interim="";for(let i=e.resultIndex;i<e.results.length;i++){const t=e.results[i][0].transcript;e.results[i].isFinal?final+=t:interim+=t} transcript.value=final||interim;status.textContent=final?"Ready to send":"Listening…"};
    recognition.onerror=e=>{status.textContent=`Microphone error: ${e.error}`;toast(status.textContent,"error")};
    recognition.onend=()=>{button.classList.remove("is-live");button.textContent="🎙️";$("#nbHaloOrb")?.classList.remove("listening")};
    try{recognition.start()}catch(e){status.textContent=e.message}
  }

  function openMicSheet() {
    if (!$("#nbMicSheet")) document.body.insertAdjacentHTML("beforeend", micMarkup());
    $("#nbMicClose")?.addEventListener("click", closeMicSheet,{once:true});
    $("#nbMicSend")?.addEventListener("click", sendTranscript);
    $("#nbMicButton")?.addEventListener("click", startMic);
  }

  function upgradeMobile() {
    if (!$(".mobile-main")) return;
    document.body.classList.add("nb-consumer-mode");
    const hero = $(".hero-card");
    if (hero && !$("#nbMobileOrb",hero)) {
      hero.insertAdjacentHTML("afterbegin", `<div class="nb-orb-wrap" style="min-height:150px"><div><div class="nb-orb" id="nbMobileOrb" style="width:120px;height:120px"></div><div class="nb-orb-label">Tap to speak with HALO</div></div></div>`);
      $("#nbMobileOrb")?.addEventListener("click",openMicSheet);
    }
    const ptt=$("#pushToTalk"); if(ptt){ptt.disabled=false;ptt.textContent="🎙 Talk to HALO";const clone=ptt.cloneNode(true);ptt.replaceWith(clone);clone.addEventListener("click",openMicSheet)}
    const install=$("#installApp"); if(install){install.hidden=false;install.textContent="Install App";install.addEventListener("click",()=>{if(!window.isSecureContext)toast("Open NoorBrain using HTTPS for app installation.","error");else toast("Use your browser menu and choose Add to Home Screen.")})}
  }

  function repairRefresh() {
    all("button").filter(b => /refresh/i.test(b.textContent || "")).forEach(button => {
      button.addEventListener("click", () => { button.dataset.nbBusy="1"; const old=button.textContent; button.textContent="Refreshing…"; setTimeout(()=>{button.textContent=old;button.dataset.nbBusy="";refreshHome()},900); });
    });
  }

  function mount() {
    document.body.classList.add("nb-consumer-mode");
    createHome(); upgradeMobile(); repairRefresh();
    window.NoorBrainPremiumUI={version:VERSION,refresh:refreshHome,openMic:openMicSheet};
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",mount); else mount();
})();
