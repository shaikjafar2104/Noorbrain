(() => {
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
