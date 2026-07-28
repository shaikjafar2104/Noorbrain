(() => {
  "use strict";

  const API = "/api/smart-automation";
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json"},
      ...options
    });

    const body = await response.json();

    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return body;
  }

  function findReminderPage() {
    return (
      document.getElementById("page-reminder-rules")
      || document.getElementById("page-rules")
      || document.querySelector('[data-page="reminder-rules"]')?.closest(".page")
    );
  }

  function findMain() {
    return document.querySelector("main.main")
      || document.querySelector("main")
      || document.querySelector(".main");
  }

  function ensurePanel() {
    const host = findReminderPage() || findMain();

    if (!host) return false;

    if (!$("smartAutomationPanel")) {
      const panel = document.createElement("section");
      panel.id = "smartAutomationPanel";
      panel.className = "card";
      panel.innerHTML = `
        <div class="card-head">
          <div>
            <h2>Smart Automation</h2>
            <p>Rules and schedules</p>
          </div>
          <button id="automationRefresh" class="button secondary">Refresh</button>
        </div>

        <div style="display:grid;gap:10px;margin-bottom:16px">
          <input id="automationName" value="Hall Presence Rule" placeholder="Rule name">
          <textarea id="automationConditions" rows="5">[
  {"kind":"zone","operator":"eq","value":"Hall"},
  {"kind":"presence_count","operator":"gte","value":1}
]</textarea>
          <textarea id="automationActions" rows="4">[
  {"kind":"halo","name":"speak","arguments":{"text":"Someone is in the Hall."}}
]</textarea>
          <button id="automationCreate" class="button success">Create Rule</button>
        </div>

        <div id="automationSummary">Loading…</div>
        <div id="automationRules">No rules.</div>
      `;
      host.appendChild(panel);

      $("automationRefresh")?.addEventListener("click", load);
      $("automationCreate")?.addEventListener("click", createRule);
    }

    return true;
  }

  async function createRule() {
    try {
      const name = $("automationName")?.value?.trim();
      const conditions = JSON.parse(
        $("automationConditions")?.value || "[]"
      );
      const actions = JSON.parse(
        $("automationActions")?.value || "[]"
      );

      await api("/rules", {
        method: "POST",
        body: JSON.stringify({
          name,
          condition_mode: "all",
          conditions,
          schedule: {"kind": "manual"},
          actions
        })
      });

      await load();
    } catch (error) {
      alert(`Rule creation failed: ${error.message}`);
    }
  }

  async function deleteRule(ruleId, name) {
    if (!confirm(`Delete automation rule "${name}"?`)) return;

    await api(`/rules/${encodeURIComponent(ruleId)}`, {
      method: "DELETE"
    });

    await load();
  }

  async function load() {
    try {
      const [health, rules] = await Promise.all([
        api("/health"),
        api("/rules")
      ]);

      $("automationSummary").textContent =
        `${health.rule_count} rules · ${health.run_count} runs`;

      $("automationRules").innerHTML = rules.rules?.length
        ? rules.rules.map(rule => `
            <div style="display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.07)">
              <div>
                <strong>${rule.name}</strong><br>
                <small>${rule.enabled ? "Enabled" : "Disabled"} · ${rule.schedule?.kind || "manual"}</small>
              </div>
              <button
                class="button danger automation-delete"
                data-id="${rule.id}"
                data-name="${rule.name}"
              >Delete</button>
            </div>
          `).join("")
        : "No rules.";

      $("automationRules")
        .querySelectorAll(".automation-delete")
        .forEach(button => {
          button.addEventListener("click", () => {
            deleteRule(
              button.dataset.id,
              button.dataset.name
            );
          });
        });
    } catch (error) {
      $("automationSummary").textContent =
        `Smart Automation unavailable: ${error.message}`;
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

  window.NoorBrainSmartAutomation = {
    mount,
    refresh: load
  };
})();
