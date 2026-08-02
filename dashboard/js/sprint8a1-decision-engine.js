(() => {
  "use strict";

  if (window.NoorBrainSprint8A1Decision) return;

  const API = "/api/halo-decision-v8";

  const state = {
    engine: null,
    topDecision: null,
  };

  const $ = id => document.getElementById(id);

  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      cache: "no-store",
      ...options,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return data;
  }

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function mount() {
    const halo =
      document.querySelector("#nbs4HALO")
      || document.querySelector(".nbv2-halo-section")
      || document.querySelector("#nbv2Halo")
      || document.querySelector("main");

    if (!halo || $("nbs8a1Decision")) return;

    const panel = document.createElement("section");
    panel.id = "nbs8a1Decision";
    panel.className = "nbs8a1-panel";

    panel.innerHTML = `
      <article class="nbs8a1-card">
        <div class="nbs8a1-head">
          <div>
            <small>SPRINT 8A.1</small>
            <h2>HALO Decision Engine</h2>
          </div>
          <div class="nbs8a1-actions">
            <button class="nbs8a1-button" id="nbs8a1Refresh">↻</button>
            <button class="nbs8a1-button primary" id="nbs8a1Add">＋ Decision</button>
          </div>
        </div>

        <div class="nbs8a1-hero">
          <div>
            <small>PROACTIVE AI CORE</small>
            <h3 id="nbs8a1TopTitle">No decision queued</h3>
            <span id="nbs8a1TopAction">HALO is observing context.</span>
          </div>
          <div class="nbs8a1-score">
            <small>Priority</small>
            <b id="nbs8a1TopScore">0%</b>
          </div>
        </div>

        <div class="nbs8a1-grid" id="nbs8a1Metrics"></div>
        <p class="nbs8a1-status" id="nbs8a1Status">Loading decision engine…</p>
      </article>

      <article class="nbs8a1-card">
        <div class="nbs8a1-head">
          <div>
            <small>CONTEXT</small>
            <h2>Live Context Score</h2>
          </div>
          <div class="nbs8a1-actions">
            <button class="nbs8a1-button primary" id="nbs8a1SaveContext">Update</button>
          </div>
        </div>

        <div class="nbs8a1-context">
          ${contextControl("presence", "Presence")}
          ${contextControl("vision", "Vision")}
          ${contextControl("prayer", "Prayer")}
          ${contextControl("habit", "Habit")}
          ${contextControl("urgency", "Urgency")}
          ${contextControl("time_relevance", "Time relevance")}
        </div>
      </article>

      <article class="nbs8a1-card">
        <div class="nbs8a1-head">
          <div>
            <small>PRIORITY QUEUE</small>
            <h2>Pending Decisions</h2>
          </div>
          <div class="nbs8a1-actions">
            <button class="nbs8a1-button danger" id="nbs8a1Clear">Clear Queue</button>
          </div>
        </div>
        <div class="nbs8a1-grid" id="nbs8a1Queue"></div>
      </article>

      <article class="nbs8a1-card">
        <div class="nbs8a1-head">
          <div>
            <small>SETTINGS</small>
            <h2>Decision Policy</h2>
          </div>
          <div class="nbs8a1-actions">
            <button class="nbs8a1-button primary" id="nbs8a1SaveSettings">Save</button>
          </div>
        </div>

        <div class="nbs8a1-settings">
          <label>
            Engine
            <select id="nbs8a1Enabled">
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </label>

          <label>
            Minimum score
            <input id="nbs8a1Minimum" type="number" min="0" max="1" step="0.05">
          </label>

          <label>
            Maximum queue
            <input id="nbs8a1MaxQueue" type="number" min="1" max="500">
          </label>

          <label>
            Auto-expire seconds
            <input id="nbs8a1Expiry" type="number" min="60">
          </label>
        </div>
      </article>
    `;

    halo.insertAdjacentElement("afterend", panel);

    if (!$("nbs8a1Modal")) {
      const modal = document.createElement("div");
      modal.id = "nbs8a1Modal";
      modal.className = "nbs8a1-modal";
      modal.hidden = true;
      document.body.appendChild(modal);
    }

    bind();
    load();
  }

  function contextControl(id, label) {
    return `
      <label>
        ${label}: <span id="nbs8a1Value-${id}">0.00</span>
        <input
          id="nbs8a1Context-${id}"
          type="range"
          min="0"
          max="1"
          step="0.05"
          value="0"
        >
      </label>
    `;
  }

  function bind() {
    $("nbs8a1Refresh").onclick = load;
    $("nbs8a1Add").onclick = addDecisionModal;
    $("nbs8a1SaveContext").onclick = saveContext;
    $("nbs8a1Clear").onclick = clearQueue;
    $("nbs8a1SaveSettings").onclick = saveSettings;

    for (const key of [
      "presence",
      "vision",
      "prayer",
      "habit",
      "urgency",
      "time_relevance",
    ]) {
      const input = $(`nbs8a1Context-${key}`);
      input.oninput = () => {
        $(`nbs8a1Value-${key}`).textContent =
          Number(input.value).toFixed(2);
      };
    }
  }

  async function load() {
    try {
      const data = await request(`${API}/state`);
      state.engine = data.decision_engine;
      state.topDecision = data.top_decision;

      renderHero();
      renderMetrics();
      renderContext();
      renderQueue();
      renderSettings();

      $("nbs8a1Status").textContent =
        `${state.engine.queue.length} queued · ${state.engine.history.length} history`;

    } catch (error) {
      $("nbs8a1Status").textContent = error.message;
    }
  }

  function renderHero() {
    if (!state.topDecision) {
      $("nbs8a1TopTitle").textContent = "No decision queued";
      $("nbs8a1TopAction").textContent = "HALO is observing context.";
      $("nbs8a1TopScore").textContent = "0%";
      return;
    }

    $("nbs8a1TopTitle").textContent = state.topDecision.title;
    $("nbs8a1TopAction").textContent = state.topDecision.action;
    $("nbs8a1TopScore").textContent =
      `${Math.round(Number(state.topDecision.priority_score || 0) * 100)}%`;
  }

  function renderMetrics() {
    const context = state.engine.context;

    $("nbs8a1Metrics").innerHTML = `
      <article class="nbs8a1-metric">
        <span>Queue</span>
        <b>${state.engine.queue.length}</b>
      </article>
      <article class="nbs8a1-metric">
        <span>History</span>
        <b>${state.engine.history.length}</b>
      </article>
      <article class="nbs8a1-metric">
        <span>Urgency</span>
        <b>${Math.round(Number(context.urgency || 0) * 100)}%</b>
      </article>
      <article class="nbs8a1-metric">
        <span>Prayer context</span>
        <b>${Math.round(Number(context.prayer || 0) * 100)}%</b>
      </article>
    `;
  }

  function renderContext() {
    for (const [key, value] of Object.entries(state.engine.context)) {
      const input = $(`nbs8a1Context-${key}`);
      const label = $(`nbs8a1Value-${key}`);

      if (input) input.value = Number(value || 0);
      if (label) label.textContent = Number(value || 0).toFixed(2);
    }
  }

  function renderQueue() {
    const host = $("nbs8a1Queue");

    if (!state.engine.queue.length) {
      host.innerHTML = `
        <div class="nbs8a1-empty">
          No proactive decisions waiting.
        </div>
      `;
      return;
    }

    host.innerHTML = state.engine.queue.map(item => `
      <article class="nbs8a1-decision">
        <b>${safe(item.title)}</b>
        <small>${safe(item.action)}</small>
        <small>${safe(item.category)} · ${safe(item.source)}</small>
        <div class="nbs8a1-priority">
          ${Math.round(Number(item.priority_score || 0) * 100)}%
        </div>
        <div class="nbs8a1-decision-actions">
          <button
            class="nbs8a1-button primary"
            data-resolve="${safe(item.id)}"
          >Resolve</button>
        </div>
      </article>
    `).join("");

    host.querySelectorAll("[data-resolve]").forEach(button => {
      button.onclick = () => resolveDecision(button.dataset.resolve);
    });
  }

  function renderSettings() {
    const settings = state.engine.settings;

    $("nbs8a1Enabled").value = String(settings.enabled !== false);
    $("nbs8a1Minimum").value = Number(settings.minimum_score || 0.55);
    $("nbs8a1MaxQueue").value = Number(settings.max_queue || 50);
    $("nbs8a1Expiry").value = Number(settings.auto_expire_seconds || 1800);
  }

  async function saveContext() {
    const context = {};

    for (const key of [
      "presence",
      "vision",
      "prayer",
      "habit",
      "urgency",
      "time_relevance",
    ]) {
      context[key] = Number($(`nbs8a1Context-${key}`).value);
    }

    try {
      const data = await request(`${API}/context`, {
        method: "POST",
        body: JSON.stringify(context),
      });

      $("nbs8a1Status").textContent =
        `Context score updated: ${Math.round(data.score * 100)}%`;

      await load();
    } catch (error) {
      $("nbs8a1Status").textContent = error.message;
    }
  }

  async function saveSettings() {
    try {
      await request(`${API}/settings`, {
        method: "POST",
        body: JSON.stringify({
          enabled: $("nbs8a1Enabled").value === "true",
          minimum_score: Number($("nbs8a1Minimum").value),
          max_queue: Number($("nbs8a1MaxQueue").value),
          auto_expire_seconds: Number($("nbs8a1Expiry").value),
        }),
      });

      $("nbs8a1Status").textContent = "Decision policy saved.";
      await load();
    } catch (error) {
      $("nbs8a1Status").textContent = error.message;
    }
  }

  async function clearQueue() {
    if (!confirm("Clear all queued decisions?")) return;

    try {
      const data = await request(`${API}/queue`, {
        method: "DELETE",
      });

      $("nbs8a1Status").textContent =
        `${data.count} decisions cleared.`;

      await load();
    } catch (error) {
      $("nbs8a1Status").textContent = error.message;
    }
  }

  async function resolveDecision(decisionId) {
    try {
      await request(`${API}/decisions/${decisionId}/resolve`, {
        method: "POST",
        body: JSON.stringify({
          status: "resolved",
          result: {source: "mobile"},
        }),
      });

      $("nbs8a1Status").textContent = "Decision resolved.";
      await load();
    } catch (error) {
      $("nbs8a1Status").textContent = error.message;
    }
  }

  function modal(html) {
    const host = $("nbs8a1Modal");
    host.hidden = false;
    host.innerHTML = html;

    host.querySelector("[data-close]")?.addEventListener("click", () => {
      host.hidden = true;
    });
  }

  function addDecisionModal() {
    modal(`
      <form class="nbs8a1-modal-card" id="nbs8a1DecisionForm">
        <h2>Add Decision</h2>

        <label>
          Title
          <input name="title" required placeholder="Remind evening Azkar">
        </label>

        <label>
          Action
          <input name="action" required placeholder="speak:islamic-reminder">
        </label>

        <label>
          Category
          <select name="category">
            <option value="general">General</option>
            <option value="islamic">Islamic</option>
            <option value="smart-home">Smart Home</option>
            <option value="vision">Vision</option>
            <option value="family">Family</option>
          </select>
        </label>

        <label>
          Message
          <textarea name="message" placeholder="Optional HALO message"></textarea>
        </label>

        <label>
          Manual priority
          <input
            name="manual_priority"
            type="number"
            min="0"
            max="1"
            step="0.05"
            value="0.5"
          >
        </label>

        <div class="nbs8a1-modal-actions">
          <button type="button" class="nbs8a1-button" data-close>Cancel</button>
          <button class="nbs8a1-button primary" type="submit">Queue Decision</button>
        </div>
      </form>
    `);

    $("nbs8a1DecisionForm").onsubmit = async event => {
      event.preventDefault();

      const values = Object.fromEntries(
        new FormData(event.target).entries()
      );

      values.manual_priority = Number(values.manual_priority);

      try {
        const result = await request(`${API}/decisions`, {
          method: "POST",
          body: JSON.stringify(values),
        });

        $("nbs8a1Modal").hidden = true;
        $("nbs8a1Status").textContent =
          `Decision ${result.status}.`;

        await load();
      } catch (error) {
        $("nbs8a1Status").textContent = error.message;
      }
    };
  }

  window.NoorBrainSprint8A1Decision = {
    version: "8.1.0",
    load,
    saveContext,
    clearQueue,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
