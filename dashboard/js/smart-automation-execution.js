(() => {
  "use strict";

  const API = "/api/smart-automation";
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json"
      },
      ...options
    });

    const body = await response.json();

    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return body;
  }

  function host() {
    return document.getElementById("smartAutomationPanel")
      || document.getElementById("page-reminder-rules")
      || document.querySelector("main.main")
      || document.querySelector("main");
  }

  function ensurePanel() {
    const target = host();

    if (!target) return false;

    if (!$("automationExecutionPanel")) {
      const panel = document.createElement("section");
      panel.id = "automationExecutionPanel";
      panel.className = "card";
      panel.innerHTML = `
        <div class="card-head">
          <div>
            <h2>Automation Execution</h2>
            <p>Safe actions, confirmations and analytics</p>
          </div>
          <button id="automationExecutionRefresh" class="button secondary">Refresh</button>
        </div>

        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">
          <input id="automationExecutionZone" value="Hall" placeholder="Zone">
          <button id="automationExecuteDry" class="button secondary">Evaluate</button>
          <button id="automationExecuteConfirmed" class="button success">Execute Confirmed</button>
        </div>

        <div id="automationExecutionSummary">Loading…</div>
        <pre id="automationExecutionResult">Ready</pre>
        <div id="automationRunHistory">No runs yet.</div>
      `;
      target.appendChild(panel);

      $("automationExecutionRefresh")?.addEventListener("click", load);
      $("automationExecuteDry")?.addEventListener("click", () => execute(false));
      $("automationExecuteConfirmed")?.addEventListener("click", () => execute(true));
    }

    return true;
  }

  async function execute(confirmed) {
    try {
      const result = await api("/execute", {
        method: "POST",
        body: JSON.stringify({
          event_type: "manual_dashboard",
          zone: $("automationExecutionZone")?.value?.trim() || null,
          force: true,
          confirmed
        })
      });

      $("automationExecutionResult").textContent =
        JSON.stringify(result, null, 2);

      await load();
    } catch (error) {
      $("automationExecutionResult").textContent =
        `Execution failed: ${error.message}`;
    }
  }

  async function load() {
    try {
      const [analytics, runs] = await Promise.all([
        api("/analytics"),
        api("/runs?limit=50")
      ]);

      $("automationExecutionSummary").textContent =
        `${analytics.enabled_rule_count}/${analytics.rule_count} enabled · ${analytics.run_count} runs`;

      $("automationRunHistory").innerHTML = runs.runs?.length
        ? runs.runs.map(run => `
            <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.07)">
              <strong>${run.rule_name || run.rule_id}</strong><br>
              <small>${run.created_at} · ${run.status}</small>
            </div>
          `).join("")
        : "No runs yet.";
    } catch (error) {
      $("automationExecutionSummary").textContent =
        `Automation analytics unavailable: ${error.message}`;
    }
  }

  function mount() {
    const ready = ensurePanel();

    if (ready) load();

    return ready;
  }

  if (!mount()) {
    const observer = new MutationObserver(() => {
      if (mount()) observer.disconnect();
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true
    });

    setTimeout(() => observer.disconnect(), 20000);
  }

  window.NoorBrainAutomationExecution = {
    mount,
    refresh: load
  };
})();
