(() => {
  "use strict";

  if (window.NoorBrainMobileAI?.installed) return;

  const API = "/api/ai-control-center-v8";

  async function request(path) {
    const response = await fetch(API + path, {cache: "no-store"});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = String(value ?? 0);
  }

  function ensurePanel() {
    let panel = document.getElementById("nbMobileAiCenterV8");
    if (panel) return panel;

    const host =
      document.querySelector(".mobile-main") ||
      document.querySelector("main") ||
      document.querySelector("#app") ||
      document.body;

    panel = document.createElement("section");
    panel.id = "nbMobileAiCenterV8";
    panel.className = "nb-mobile-ai";
    panel.innerHTML = `
      <div class="nb-mobile-ai__hero">
        <div class="nb-mobile-ai__orb" aria-hidden="true"></div>
        <div>
          <span>HALO INTELLIGENCE</span>
          <h2>AI Control Center</h2>
          <p id="nbMobileAiStatus">Loading your home intelligence…</p>
        </div>
        <button id="nbMobileAiRefresh" type="button" aria-label="Refresh AI center">↻</button>
      </div>
      <div class="nb-mobile-ai__grid">
        <button type="button" data-ai-target="memory">
          <strong id="nbMobileAiSessions">0</strong>
          <span>Memory</span>
          <small id="nbMobileAiMessages">0 messages</small>
        </button>
        <button type="button" data-ai-target="routines">
          <strong id="nbMobileAiActivities">0</strong>
          <span>Activities</span>
          <small id="nbMobileAiHabits">0 habits</small>
        </button>
        <button type="button" data-ai-target="voice">
          <strong>Ready</strong>
          <span>Voice context</span>
          <small>Conversation aware</small>
        </button>
        <button type="button" data-ai-target="facts">
          <strong id="nbMobileAiFacts">0</strong>
          <span>Personal facts</span>
          <small>Private memory</small>
        </button>
      </div>
      <div class="nb-mobile-ai__footer">
        <span class="nb-mobile-ai__live">● AI online</span>
        <span id="nbMobileAiVersion">v8.5.0</span>
      </div>
    `;

    const firstCard = host.querySelector("section, .mobile-card, .card");
    if (firstCard) {
      firstCard.insertAdjacentElement("beforebegin", panel);
    } else {
      host.appendChild(panel);
    }

    panel.querySelector("#nbMobileAiRefresh")
      ?.addEventListener("click", refresh);
    panel.querySelectorAll("[data-ai-target]").forEach(button => {
      button.addEventListener("click", () => {
        panel.querySelectorAll("[data-ai-target]")
          .forEach(item => item.classList.remove("is-selected"));
        button.classList.add("is-selected");
      });
    });
    return panel;
  }

  async function refresh() {
    const panel = ensurePanel();
    const status = panel.querySelector("#nbMobileAiStatus");
    const button = panel.querySelector("#nbMobileAiRefresh");
    if (button) button.disabled = true;
    if (status) status.textContent = "Refreshing intelligence…";

    try {
      const data = await request("/overview");
      const memory = data.conversation_memory || {};
      const routine = data.routine_intelligence || {};
      setText("nbMobileAiSessions", memory.sessions);
      setText("nbMobileAiMessages", `${memory.messages || 0} messages`);
      setText("nbMobileAiFacts", memory.facts);
      setText("nbMobileAiActivities", routine.activities);
      setText("nbMobileAiHabits", `${routine.habits || 0} habits`);
      setText("nbMobileAiVersion", `v${data.version}`);
      if (status) status.textContent = "Your home intelligence is ready";
      panel.classList.add("is-online");
    } catch (error) {
      if (status) status.textContent = `AI unavailable: ${error.message}`;
      panel.classList.remove("is-online");
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

  window.NoorBrainMobileAI = Object.freeze({
    installed: true,
    version: "8.5.1",
    refresh,
  });
})();
