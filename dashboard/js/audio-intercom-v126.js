(() => {
  "use strict";

  const API = "/api/playback";
  const state = {
    nodes: [],
    media: [],
    listenSession: "",
    listenActive: false,
    talkMode: "idle",
    talkSession: "",
    talkTarget: "",
    recorder: null,
    stream: null,
    chunks: [],
  };

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[character]);
  }

  async function request(path, options = {}) {
    const timeoutMs = Number(options.timeout || 130000);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const cleanOptions = {...options};
    delete cleanOptions.timeout;
    let response;
    try {
      response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json", ...(options.headers || {})},
      signal: controller.signal,
      ...cleanOptions,
      });
    } catch (error) {
      if (error?.name === "AbortError") throw new Error("The room node request timed out.");
      throw error;
    } finally {
      clearTimeout(timer);
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    return payload;
  }

  function isNative() {
    return new URLSearchParams(location.search).get("native_app") === "1" && window.parent !== window;
  }

  function status(message, mode = "") {
    const node = document.getElementById("nbAudioStatus");
    if (node) {
      node.textContent = message;
      node.dataset.mode = mode;
    }
  }

  function talkError(error) {
    state.talkMode = "idle";
    state.stream?.getTracks?.().forEach(track => track.stop());
    const label = document.getElementById("nbTalkState");
    if (label) label.textContent = `Error · ${error?.message || error}`;
    const start = document.getElementById("nbTalkStart");
    const stop = document.getElementById("nbTalkStop");
    if (start) start.disabled = false;
    if (stop) stop.disabled = true;
  }

  function targetOptions(selected = "") {
    return `<option value="">Select a Raspberry Pi speaker</option>${state.nodes.map(node => `<option value="${esc(node.node_id)}" ${node.node_id === selected ? "selected" : ""}>${esc(node.name)} · ${esc(node.room)}${node.online === false ? " · Offline" : ""}</option>`).join("")}`;
  }

  function mediaOptions() {
    return `<option value="">Select media</option>${state.media.map(item => `<option value="${esc(item.id)}">${esc(item.name || item.original_filename)} · ${esc(item.category || "media")}</option>`).join("")}`;
  }

  function pageMarkup() {
    return `<section class="nb126-page nb-audio-page">
      <section class="nb126-page-head"><small>ROOM AUDIO</small><h1>Rooms & Speakers</h1><p>Play and communicate through a selected Raspberry Pi room node.</p></section>
      <section class="nb126-section"><div class="nb126-section-title"><div><small>NODES</small><h2>Raspberry Pi Nodes</h2></div><button id="nbNodeAdd" type="button">+ Add</button></div>
        <div id="nbNodeList" class="nb126-grid">${state.nodes.length ? state.nodes.map(node => `<article class="nb126-card"><div><small>${node.online ? "ONLINE" : node.online === false ? "OFFLINE" : "CONFIGURED"}</small><h3>${esc(node.name)}</h3><p>${esc(node.room)} · ${node.capabilities?.camera ? "Camera " : ""}${node.capabilities?.microphone ? "Mic " : ""}${node.capabilities?.speaker ? "Speaker" : ""}</p><small>${node.trusted ? "Trusted" : "Trust token required"}</small></div><div class="nb126-card-actions"><button data-node-edit="${esc(node.node_id)}">Manage</button><button data-node-delete="${esc(node.node_id)}">Delete</button></div></article>`).join("") : `<div class="nb126-card"><b>No room nodes configured</b><small>Add the existing Pi node; no device data is fabricated.</small></div>`}</div>
      </section>
      <section class="nb126-section"><div class="nb126-card"><small>PLAY MESSAGE</small><h2>Play on Room Speaker</h2>
        <div class="nb126-form-card"><label class="nb126-field">Message type<select id="nbPlayType"><option value="tts">Text / TTS Message</option><option value="media">Existing Media</option><option value="dua">Dua</option><option value="azkar">Azkar</option><option value="reminder_audio">Reminder Audio</option></select></label>
        <label class="nb126-field" id="nbPlayTextWrap">Message<textarea id="nbPlayText" placeholder="Please remember to take your keys"></textarea></label>
        <label class="nb126-field" id="nbPlayMediaWrap" hidden>Message / Media<select id="nbPlayMedia">${mediaOptions()}</select></label>
        <label class="nb126-field">Target Room / Raspberry Pi<select id="nbPlayTarget">${targetOptions()}</select></label>
        <label class="nb126-field">Volume<input id="nbPlayVolume" type="range" min="0" max="100" value="80"></label>
        <div class="nb126-card-actions"><button id="nbPlay" class="nb126-button-primary" type="button">Play</button><button id="nbStop" type="button">Stop</button></div></div>
      </div></section>
      <section class="nb126-section"><div class="nb126-grid">
        <div class="nb126-card"><small>PI MIC → PHONE</small><h3>Listen to Room</h3><p id="nbListenState">OFF · Listening never starts automatically.</p><label class="nb126-field">Room<select id="nbListenTarget">${targetOptions()}</select></label><div class="nb126-card-actions"><button id="nbListenStart">Start Listening</button><button id="nbListenStop" disabled>Stop Listening</button></div></div>
        <div class="nb126-card"><small>PHONE MIC → PI</small><h3>Talk to Room</h3><p id="nbTalkState">Stopped</p><label class="nb126-field">Room<select id="nbTalkTarget">${targetOptions()}</select></label><div class="nb126-card-actions"><button id="nbTalkStart">Start Talking</button><button id="nbTalkStop" disabled>Stop & Send</button></div></div>
      </div></section>
      <p id="nbAudioStatus" class="nb126-card">Ready. Home audio never falls back to this laptop.</p>
      <dialog id="nbNodeDialog"><form id="nbNodeForm" method="dialog" class="nb126-form-card"><h2 id="nbNodeFormTitle">Add Raspberry Pi Node</h2><input id="nbNodeId" type="hidden"><label class="nb126-field">Name<input id="nbNodeName" required placeholder="Hall Pi"></label><label class="nb126-field">Room<input id="nbNodeRoom" required placeholder="Hall"></label><label class="nb126-field">URL<input id="nbNodeUrl" required placeholder="http://192.168.2.29:8010"></label><label class="nb126-field">Trust token<input id="nbNodeToken" type="password" placeholder="Node token"></label><label><input id="nbNodeCamera" type="checkbox"> Camera</label><label><input id="nbNodeMic" type="checkbox" checked> Microphone</label><label><input id="nbNodeSpeaker" type="checkbox" checked> Speaker / Playback</label><div class="nb126-card-actions"><button value="cancel">Cancel</button><button id="nbNodeSave" value="default">Save</button></div></form></dialog>
    </section>`;
  }

  async function load() {
    const [nodes, media] = await Promise.all([
      request("/nodes?probe=true"),
      fetch("/api/media", {cache: "no-store"}).then(response => response.json()),
    ]);
    state.nodes = nodes.nodes || [];
    state.media = media.items || media.media || [];
  }

  async function open() {
    try { await load(); } catch (error) { status(error.message, "error"); }
    const content = document.getElementById("nb126Content");
    let host = content;
    if (!host) {
      host = document.getElementById("nbAudioDesktopHost") || document.body.appendChild(Object.assign(document.createElement("div"), {id: "nbAudioDesktopHost"}));
      host.style.cssText = "position:fixed;inset:64px 24px 24px 330px;z-index:10000;overflow:auto;background:#101b2d;padding:24px;border-radius:20px;color:white";
    }
    host.innerHTML = pageMarkup();
    document.body.dataset.nb126Page = "audio-intercom";
    bind();
    return true;
  }

  function openNode(node = null) {
    document.getElementById("nbNodeFormTitle").textContent = node ? "Manage Raspberry Pi Node" : "Add Raspberry Pi Node";
    document.getElementById("nbNodeId").value = node?.node_id || "";
    document.getElementById("nbNodeName").value = node?.name || "";
    document.getElementById("nbNodeRoom").value = node?.room || "";
    document.getElementById("nbNodeUrl").value = node?.url || "";
    document.getElementById("nbNodeToken").value = "";
    document.getElementById("nbNodeCamera").checked = !!node?.capabilities?.camera;
    document.getElementById("nbNodeMic").checked = node ? !!node.capabilities?.microphone : true;
    document.getElementById("nbNodeSpeaker").checked = node ? !!node.capabilities?.speaker : true;
    document.getElementById("nbNodeDialog").showModal();
  }

  async function saveNode(event) {
    event.preventDefault();
    const id = document.getElementById("nbNodeId").value;
    const token = document.getElementById("nbNodeToken").value;
    const payload = {
      name: document.getElementById("nbNodeName").value,
      room: document.getElementById("nbNodeRoom").value,
      url: document.getElementById("nbNodeUrl").value,
      capabilities: {camera: document.getElementById("nbNodeCamera").checked, microphone: document.getElementById("nbNodeMic").checked, speaker: document.getElementById("nbNodeSpeaker").checked, playback: document.getElementById("nbNodeSpeaker").checked},
    };
    if (token) payload.token = token;
    await request(id ? `/nodes/${encodeURIComponent(id)}` : "/nodes", {method: id ? "PUT" : "POST", body: JSON.stringify(payload)});
    document.getElementById("nbNodeDialog").close();
    await open();
  }

  async function play() {
    const type = document.getElementById("nbPlayType").value;
    const target = document.getElementById("nbPlayTarget").value;
    status("Sending to target speaker…", "working");
    const result = await request("/play", {method: "POST", body: JSON.stringify({target_node: target, type, content: document.getElementById("nbPlayText").value, media_id: document.getElementById("nbPlayMedia").value, volume: Number(document.getElementById("nbPlayVolume").value)})});
    status(`Played on ${result.target_name} in ${result.room}.`, "success");
  }

  async function stopPlayback() {
    const target = document.getElementById("nbPlayTarget").value;
    if (!target) throw new Error("Select a target speaker.");
    const result = await request(`/stop/${encodeURIComponent(target)}`, {method: "POST", body: "{}"});
    status(result.status === "idle" ? "Target speaker was already idle." : "Target speaker stopped.", "success");
  }

  function playChunk(encoded, format = "wav") {
    if (state.manualLocked) return;  // auto-intercom has taken over

    const binary = atob(encoded);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return new Audio(URL.createObjectURL(new Blob([bytes], {type: `audio/${format}`}))).play();
  }

  function markManualMode() {
    state.manualLocked = !!(window.NoorBrainAutoIntercomV126 && window.NoorBrainAutoIntercomV126.isEnabled && window.NoorBrainAutoIntercomV126.isEnabled());
  }

  window.NoorBrainAudioIntercomV126 = window.NoorBrainAudioIntercomV126 || {};
  window.NoorBrainAudioIntercomV126.stopListen = stopListen;
  window.addEventListener("noorbrain:auto-intercom-state-changed", () => markManualMode());

  async function listenLoop() {
    while (state.listenActive && state.listenSession) {
      try {
        const chunk = await request(`/listen/${encodeURIComponent(state.listenSession)}/chunk?seconds=1`, {method: "POST", body: "{}"});
        if (!state.listenActive) break;
        await playChunk(chunk.audio_base64, chunk.format);
      } catch (error) {
        state.listenActive = false;
        const failedSession = state.listenSession;
        state.listenSession = "";
        if (failedSession) request(`/listen/${encodeURIComponent(failedSession)}/stop`, {method:"POST", body:"{}", timeout:10000}).catch(() => {});
        document.getElementById("nbListenState").textContent = `Error · ${error.message}`;
        document.getElementById("nbListenStart").disabled = false;
        document.getElementById("nbListenStop").disabled = true;
      }
    }
  }

  async function startListen() {
    if (state.talkMode !== "idle") throw new Error("Stop talking before listening to the room.");
    const target = document.getElementById("nbListenTarget").value;
    if (!target) throw new Error("Select a room microphone.");
    document.getElementById("nbListenState").textContent = "Connecting…";
    const result = await request(`/listen/start/${encodeURIComponent(target)}`, {method: "POST", body: "{}"});
    state.listenSession = result.session_id;
    state.listenActive = true;
    document.getElementById("nbListenState").textContent = `LIVE ROOM AUDIO · ${result.room} · Listening…`;
    document.getElementById("nbListenStart").disabled = true;
    document.getElementById("nbListenStop").disabled = false;
    listenLoop();
  }

  async function stopListen() {
    state.listenActive = false;
    const session = state.listenSession;
    state.listenSession = "";
    if (session) await request(`/listen/${encodeURIComponent(session)}/stop`, {method: "POST", body: "{}"});
    document.getElementById("nbListenState").textContent = "OFF · Listening stopped.";
    document.getElementById("nbListenStart").disabled = false;
    document.getElementById("nbListenStop").disabled = true;
  }

  async function startTalk() {
    const target = document.getElementById("nbTalkTarget").value;
    if (!target) throw new Error("Select a target room speaker.");
    if (state.listenActive) await stopListen();
    state.talkTarget = target;
    state.talkSession = `intercom-${Date.now()}`;
    state.talkMode = "connecting";
    document.getElementById("nbTalkState").textContent = "Connecting…";
    if (isNative()) {
      window.parent.postMessage({type: "noorbrain-native-record-toggle", action: "start", purpose: "intercom", session_id: state.talkSession}, "*");
    } else {
      state.stream = await navigator.mediaDevices.getUserMedia({audio: true});
      state.chunks = [];
      state.recorder = new MediaRecorder(state.stream);
      state.recorder.ondataavailable = event => event.data.size && state.chunks.push(event.data);
      state.recorder.start(250);
      state.talkMode = "talking";
      document.getElementById("nbTalkState").textContent = "Talking…";
    }
    document.getElementById("nbTalkStart").disabled = true;
    document.getElementById("nbTalkStop").disabled = false;
  }

  async function sendTalkBlob(blob) {
    state.talkMode = "sending";
    document.getElementById("nbTalkState").textContent = "Sending…";
    const encoded = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onerror = reject; reader.onload = () => resolve(String(reader.result).split(",")[1]); reader.readAsDataURL(blob); });
    await request(`/talk/${encodeURIComponent(state.talkTarget)}`, {method: "POST", body: JSON.stringify({audio_base64: encoded, format: blob.type.includes("webm") ? "webm" : "m4a"})});
    state.talkMode = "idle";
    document.getElementById("nbTalkState").textContent = "Played on room speaker.";
    document.getElementById("nbTalkStart").disabled = false;
    document.getElementById("nbTalkStop").disabled = true;
  }

  async function stopTalk() {
    document.getElementById("nbTalkState").textContent = "Sending…";
    if (isNative()) {
      window.parent.postMessage({type: "noorbrain-native-record-toggle", action: "stop", purpose: "intercom", session_id: state.talkSession}, "*");
      return;
    }
    const recorder = state.recorder;
    const stopped = new Promise(resolve => recorder.addEventListener("stop", resolve, {once: true}));
    recorder.stop();
    await stopped;
    state.stream?.getTracks().forEach(track => track.stop());
    await sendTalkBlob(new Blob(state.chunks, {type: recorder.mimeType || "audio/webm"}));
  }

  function bind() {
    // When auto-intercom is active, manual Listen/Talk buttons are disabled.
    const autoMod = window.NoorBrainAutoIntercomV126;
    if (autoMod && autoMod.isEnabled && autoMod.isEnabled()) {
      const lb = document.getElementById("nbListenStart");
      const ls = document.getElementById("nbListenStop");
      const tb = document.getElementById("nbTalkStart");
      const ts = document.getElementById("nbTalkStop");
      if (lb) lb.disabled = true;
      if (ls) ls.disabled = true;
      if (tb) tb.disabled = true;
      if (ts) ts.disabled = true;
      const st = document.getElementById("nbListenState");
      if (st) st.textContent = "AUTO · Listening to Room (auto intercom active)";
      const tt = document.getElementById("nbTalkState");
      if (tt) tt.textContent = "AUTO · Talk handled automatically";
    }
    document.getElementById("nbNodeAdd").onclick = () => openNode();
    document.querySelectorAll("[data-node-edit]").forEach(button => button.onclick = () => openNode(state.nodes.find(node => node.node_id === button.dataset.nodeEdit)));
    document.querySelectorAll("[data-node-delete]").forEach(button => button.onclick = async () => { if (confirm("Delete this room node configuration?")) { await request(`/nodes/${encodeURIComponent(button.dataset.nodeDelete)}`, {method: "DELETE"}); await open(); } });
    document.getElementById("nbNodeForm").onsubmit = event => saveNode(event).catch(error => status(error.message, "error"));
    document.getElementById("nbPlayType").onchange = event => { const media = event.target.value !== "tts"; document.getElementById("nbPlayMediaWrap").hidden = !media; document.getElementById("nbPlayTextWrap").hidden = media; };
    document.getElementById("nbPlay").onclick = () => play().catch(error => status(error.message, "error"));
    document.getElementById("nbStop").onclick = () => stopPlayback().catch(error => status(error.message, "error"));
    document.getElementById("nbListenStart").onclick = () => startListen().catch(error => status(error.message, "error"));
    document.getElementById("nbListenStop").onclick = () => stopListen().catch(error => status(error.message, "error"));
    document.getElementById("nbTalkStart").onclick = () => startTalk().catch(talkError);
    document.getElementById("nbTalkStop").onclick = () => stopTalk().catch(talkError);
  }

  window.addEventListener("message", event => {
    const data = event.data || {};
    if (data.session_id !== state.talkSession) return;
    if (data.event === "RECORDING_STARTED") {
      state.talkMode = "talking";
      const node = document.getElementById("nbTalkState");
      if (node) node.textContent = "Talking…";
    }
    if (data.type === "noorbrain-native-intercom-audio") {
      const binary = atob(data.audio_base64);
      const bytes = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
      sendTalkBlob(new Blob([bytes], {type: "audio/mp4"})).catch(talkError);
    }
    if (data.event === "NATIVE_START_ERROR" || data.event === "VOICE_ERROR") {
      talkError(data.message || "Intercom microphone failed");
    }
  });

  window.addEventListener("pagehide", () => {
    if (state.listenSession) stopListen().catch(() => {});
    state.stream?.getTracks?.().forEach(track => track.stop());
  });

  document.addEventListener("click", event => {
    if (state.listenSession && event.target.closest?.("[data-nb126-route]")) {
      stopListen().catch(() => {});
    }
  }, true);

  markManualMode();

  window.NoorBrainAudioIntercom = Object.freeze({open, version: "1.0.0"});
  document.getElementById("nbAudioIntercomNav")?.addEventListener("click", event => {
    event.preventDefault();
    open().catch(error => console.error("AUDIO_INTERCOM_OPEN_FAILED", error));
  });
})();
