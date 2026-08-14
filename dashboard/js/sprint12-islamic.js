(() => {
  "use strict";

  if (window.NoorBrainIslamicV12?.installed) return;

  const API = "/api/islamic-intelligence-v12";
  const state = {rules: [], editing: null};
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json", ...(options.headers || {})},
      ...options
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function panel() {
    let root = $("nbIslamicV12");
    if (root) return root;

    root = document.createElement("section");
    root.id = "nbIslamicV12";
    root.className = "nb-i12";
    root.innerHTML = `
      <div class="nb-i12-head">
        <div>
          <small>ISLAMIC INTELLIGENCE</small>
          <h2>Smart Islamic Rules</h2>
          <p id="nbI12Status">Loading…</p>
        </div>
        <div class="ml-actions">
          <button id="nbI12Refresh" type="button">Refresh</button>
          <button id="nbI12Add" type="button">+ Add Rule</button>
        </div>
      </div>
      <div id="nbI12Summary" class="nb-i12-summary"></div>
      <form id="nbI12Form" class="ml-form card" hidden>
        <input id="nbI12Id" type="hidden">
        <label>Name<input id="nbI12Name" required maxlength="120"></label>
        <label>Event
          <select id="nbI12Event">
            <option value="person_entered">Person entered</option>
            <option value="person_exited">Person exited</option>
            <option value="time_morning">Morning time</option>
            <option value="time_evening">Evening time</option>
          </select>
        </label>
        <label>Zone<input id="nbI12Zone" maxlength="120" placeholder="Optional"></label>
        <label>Message<textarea id="nbI12Message" required rows="3"></textarea></label>
        <label><input id="nbI12RuleEnabled" type="checkbox" checked> Enabled</label>
        <div class="ml-actions">
          <button type="submit">Save Rule</button>
          <button id="nbI12Cancel" type="button">Cancel</button>
        </div>
      </form>
      <div id="nbI12Rules" class="nb-i12-rules"></div>
      <label><input id="nbI12Enabled" type="checkbox"> Proactive reminders enabled</label>
    `;

    (document.querySelector("main.main") || document.querySelector("main") || document.body)
      .appendChild(root);
    $("nbI12Refresh").onclick = load;
    $("nbI12Add").onclick = () => openEditor();
    $("nbI12Cancel").onclick = closeEditor;
    $("nbI12Form").onsubmit = save;
    $("nbI12Rules").onclick = handleAction;
    $("nbI12Enabled").onchange = event => setting(event.target.checked);
    return root;
  }

  function render() {
    const root = $("nbI12Rules");
    root.innerHTML = state.rules.length ? state.rules.map(rule => `
      <article data-rule-id="${esc(rule.id)}">
        <div>
          <b>${esc(rule.name)}</b>
          <span>${esc(rule.event)}${rule.zone ? ` · ${esc(rule.zone)}` : ""}</span>
          <small>${esc(rule.message)}</small>
        </div>
        <div class="ml-actions">
          <button data-action="toggle">${rule.enabled === false ? "Enable" : "Disable"}</button>
          <button data-action="test">Test</button>
          <button data-action="edit">Edit</button>
          <button data-action="delete">Delete</button>
        </div>
      </article>
    `).join("") : `<div class="nb-i12-empty">No Smart Islamic Rules configured.</div>`;
  }

  async function load() {
    panel();
    try {
      const data = await api("/overview");
      state.rules = data.rules || [];
      $("nbI12Summary").innerHTML =
        `<span>${data.summary.enabled} active rules</span><span>${data.summary.events} events</span>`;
      $("nbI12Enabled").checked = Boolean(data.settings.enabled);
      $("nbI12Status").textContent = `${state.rules.length} rules loaded`;
      render();
    } catch (error) {
      $("nbI12Status").textContent = `Unavailable: ${error.message}`;
    }
  }

  function openEditor(rule = null) {
    state.editing = rule?.id || null;
    $("nbI12Id").value = rule?.id || "";
    $("nbI12Name").value = rule?.name || "";
    $("nbI12Event").value = rule?.event || "person_entered";
    $("nbI12Zone").value = rule?.zone || "";
    $("nbI12Message").value = rule?.message || "";
    $("nbI12RuleEnabled").checked = rule?.enabled !== false;
    $("nbI12Form").hidden = false;
    $("nbI12Name").focus();
  }

  function closeEditor() {
    state.editing = null;
    $("nbI12Form").hidden = true;
  }

  async function save(event) {
    event.preventDefault();
    const payload = {
      name: $("nbI12Name").value.trim(),
      event: $("nbI12Event").value,
      zone: $("nbI12Zone").value.trim(),
      message: $("nbI12Message").value.trim(),
      enabled: $("nbI12RuleEnabled").checked
    };
    try {
      await api(state.editing ? `/rules/${encodeURIComponent(state.editing)}` : "/rules", {
        method: state.editing ? "PATCH" : "POST",
        body: JSON.stringify(payload)
      });
      closeEditor();
      await load();
    } catch (error) {
      $("nbI12Status").textContent = `Save failed: ${error.message}`;
    }
  }

  async function handleAction(event) {
    const button = event.target.closest("[data-action]");
    const row = button?.closest("[data-rule-id]");
    const rule = state.rules.find(item => String(item.id) === row?.dataset.ruleId);
    if (!button || !rule) return;

    try {
      if (button.dataset.action === "edit") return openEditor(rule);
      if (button.dataset.action === "delete") {
        if (!confirm(`Delete \"${rule.name}\"?`)) return;
        await api(`/rules/${encodeURIComponent(rule.id)}`, {method: "DELETE"});
      }
      if (button.dataset.action === "toggle") {
        await api(`/rules/${encodeURIComponent(rule.id)}`, {
          method: "PATCH",
          body: JSON.stringify({enabled: rule.enabled === false})
        });
      }
      if (button.dataset.action === "test") {
        const result = await api("/evaluate", {
          method: "POST",
          body: JSON.stringify({event: rule.event, zone: rule.zone || ""})
        });
        $("nbI12Status").textContent = `Test matched ${result.reminders?.length || 0} rule(s)`;
      }
      await load();
    } catch (error) {
      $("nbI12Status").textContent = `${button.dataset.action} failed: ${error.message}`;
    }
  }

  async function setting(enabled) {
    try {
      await api("/settings", {method: "PATCH", body: JSON.stringify({enabled})});
      await load();
    } catch (error) {
      $("nbI12Status").textContent = `Settings failed: ${error.message}`;
    }
  }

  function start() { panel(); load(); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else start();

  window.NoorBrainIslamicV12 = Object.freeze({
    installed: true,
    version: "12.1.0",
    load,
    refresh: load
  });
})();
