(() => {
  "use strict";

  if (window.NoorBrainAIControlCenter?.installed) return;

  const API = "/api/ai-control-center-v8";

  async function request(path) {
    const response = await fetch(API + path, {cache: "no-store"});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }
    return body;
  }

  function ensurePanel() {
    let panel = document.getElementById("nbAiControlCenterV8");
    if (panel) return panel;

    const host =
      document.querySelector("main") ||
      document.querySelector(".dashboard-main") ||
      document.querySelector(".content") ||
      document.body;

    panel = document.createElement("section");
    panel.id = "nbAiControlCenterV8";
    panel.className = "nb-ai-center";
    panel.innerHTML = `
      <div class="nb-ai-center__head">
        <div>
          <span class="nb-ai-center__eyebrow">HALO Intelligence</span>
          <h2>AI Control Center</h2>
          <p id="nbAiCenterStatus">Loading intelligence…</p>
        </div>
        <button id="nbAiCenterRefresh" type="button">Refresh</button>
      </div>
      <div class="nb-ai-center__grid">
        <article>
          <strong id="nbAiSessions">0</strong>
          <span>Memory sessions</span>
        </article>
        <article>
          <strong id="nbAiMessages">0</strong>
          <span>Remembered messages</span>
        </article>
        <article>
          <strong id="nbAiFacts">0</strong>
          <span>Personal facts</span>
        </article>
        <article>
          <strong id="nbAiActivities">0</strong>
          <span>Routine activities</span>
        </article>
      </div>
      <div class="nb-ai-center__footer">
        <span class="nb-ai-ready">Voice context ready</span>
        <span id="nbAiCenterVersion">v8.5.0</span>
      </div>
    `;

    host.appendChild(panel);
    panel.querySelector("#nbAiCenterRefresh")
      ?.addEventListener("click", refresh);
    return panel;
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = String(value ?? 0);
  }

  async function refresh() {
    const panel = ensurePanel();
    const button = panel.querySelector("#nbAiCenterRefresh");
    const status = panel.querySelector("#nbAiCenterStatus");
    if (button) button.disabled = true;
    if (status) status.textContent = "Refreshing intelligence…";

    try {
      const data = await request("/overview");
      const memory = data.conversation_memory || {};
      const routine = data.routine_intelligence || {};
      setText("nbAiSessions", memory.sessions);
      setText("nbAiMessages", memory.messages);
      setText("nbAiFacts", memory.facts);
      setText("nbAiActivities", routine.activities);
      setText("nbAiCenterVersion", `v${data.version}`);
      if (status) status.textContent = "HALO intelligence is online";
    } catch (error) {
      if (status) status.textContent = `Unavailable: ${error.message}`;
    } finally {
      if (button) button.disabled = false;
    }
  }

  function start() {
    ensurePanel();
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }

  window.NoorBrainAIControlCenter = Object.freeze({
    installed: true,
    version: "8.5.0",
    refresh,
  });
})();
