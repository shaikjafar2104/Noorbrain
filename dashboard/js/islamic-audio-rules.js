(() => {
  "use strict";
  if (window.NoorBrainIslamicAudioRules?.installed) return;

  const API = "/api/islamic-audio-rules";
  let catalog = [];
  let lastEvent = Date.now() / 1000;
  let appAudioEnabled = localStorage.getItem("nb-islamic-app-audio") === "on";

  const esc = value => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");

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

  function panel() {
    let root = document.getElementById("nbIslamicAudioRules");
    if (root) return root;
    root = document.createElement("section");
    root.id = "nbIslamicAudioRules";
    root.className = "nb-iar";
    root.innerHTML = `
      <div class="nb-iar-head">
        <div><small>ISLAMIC AUDIO</small><h2>Duas & Azkar Reminder Rules</h2>
        <p id="nbIarStatus">Loading audio…</p></div>
        <button id="nbIarSync" type="button">Refresh</button>
      </div>
      <div class="nb-iar-grid">
        <label>Audio<select id="nbIarMedia"></select></label>
        <label>Trigger<select id="nbIarTrigger">
          <option value="appeared">Person appeared</option>
          <option value="entered_zone" selected>Person entered zone</option>
          <option value="moved_zone">Person moved zone</option>
          <option value="left_zone">Person left zone</option>
          <option value="stayed">Person stayed</option>
          <option value="disappeared">Person disappeared</option>
        </select></label>
        <label>Zone<input id="nbIarZone" placeholder="Any zone"></label>
        <label>Cooldown (minutes)<input id="nbIarCooldown" type="number" min="0" value="30"></label>
      </div>
      <div class="nb-iar-actions">
        <button id="nbIarPreview" type="button">▶ Play</button>
        <button id="nbIarCreate" class="primary" type="button">+ Create Reminder Rule</button>
        <button id="nbIarAppAudio" type="button"></button>
      </div>
      <p class="nb-iar-note">Recorded MP3 only · Electronic browser voice is OFF</p>`;
    const host = document.querySelector("main.main") || document.querySelector("main") || document.body;
    host.appendChild(root);
    root.querySelector("#nbIarSync").onclick = sync;
    root.querySelector("#nbIarPreview").onclick = preview;
    root.querySelector("#nbIarCreate").onclick = createRule;
    root.querySelector("#nbIarAppAudio").onclick = toggleAppAudio;
    updateAudioButton();
    return root;
  }

  function updateAudioButton() {
    const button = document.getElementById("nbIarAppAudio");
    if (button) button.textContent = appAudioEnabled ? "App Audio: ON" : "Enable App Audio";
  }

  async function load() {
    const root = panel();
    try {
      const data = await api("/catalog");
      catalog = [...(data.duas || []), ...(data.azkar || [])];
      const select = root.querySelector("#nbIarMedia");
      select.innerHTML = "";
      for (const groupName of ["duas", "azkar"]) {
        const rows = catalog.filter(item => item.category === groupName);
        if (!rows.length) continue;
        const group = document.createElement("optgroup");
        group.label = groupName === "duas" ? "30 Duas" : "Azkar";
        for (const item of rows) {
          const option = document.createElement("option");
          option.value = item.id;
          option.textContent = item.name;
          group.appendChild(option);
        }
        select.appendChild(group);
      }
      root.querySelector("#nbIarStatus").textContent = `${data.duas?.length || 0} Duas · ${data.azkar?.length || 0} Azkar ready`;
    } catch (error) {
      root.querySelector("#nbIarStatus").textContent = error.message;
    }
  }

  async function sync() {
    await api("/sync", {method: "POST", body: "{}"});
    await load();
  }

  function selected() {
    const id = panel().querySelector("#nbIarMedia").value;
    return catalog.find(item => item.id === id);
  }

  async function preview() {
    const item = selected();
    if (!item) return;
    appAudioEnabled = true;
    localStorage.setItem("nb-islamic-app-audio", "on");
    updateAudioButton();
    const audio = new Audio(item.file_url || `/media/${item.id}/file`);
    await audio.play();
  }

  async function toggleAppAudio() {
    appAudioEnabled = !appAudioEnabled;
    localStorage.setItem("nb-islamic-app-audio", appAudioEnabled ? "on" : "off");
    updateAudioButton();
  }

  async function createRule() {
    const root = panel();
    const item = selected();
    if (!item) return;
    const payload = {
      media_id: item.id,
      name: item.name,
      message: item.name,
      trigger: root.querySelector("#nbIarTrigger").value,
      zone: root.querySelector("#nbIarZone").value.trim(),
      cooldown_seconds: Number(root.querySelector("#nbIarCooldown").value || 0) * 60,
      enabled: true,
    };
    try {
      await api("/rules", {method: "POST", body: JSON.stringify(payload)});
      root.querySelector("#nbIarStatus").textContent = `Rule created: ${item.name}`;
    } catch (error) {
      root.querySelector("#nbIarStatus").textContent = error.message;
    }
  }

  async function pollEvents() {
    if (!appAudioEnabled) return;
    try {
      const data = await api(`/events?after=${lastEvent}`);
      for (const event of data.events || []) {
        lastEvent = Math.max(lastEvent, Number(event.timestamp || 0));
        await new Audio(event.file_url).play().catch(() => {});
      }
    } catch (_) {}
  }

  function connectNavigation() {
    document.addEventListener("click", event => {
      const target = event.target.closest("button, a, [role='button'], .feature-card");
      if (!target) return;
      const text = String(target.textContent || "").trim().toLowerCase();
      if (text === "islamic" || text.includes("reminder rules")) {
        setTimeout(() => panel().scrollIntoView({behavior: "smooth", block: "start"}), 80);
      }
    });
  }

  function start() {
    panel();
    load();
    connectNavigation();
    setInterval(pollEvents, 1200);
  }

  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", start, {once: true})
    : start();
  window.NoorBrainIslamicAudioRules = Object.freeze({installed: true, load, sync});
})();
