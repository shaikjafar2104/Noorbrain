(() => {
  "use strict";
  if (window.NoorBrainPluginsV13?.installed) return;

  const API = "/api/plugin-platform-v13";
  const state = {plugins: []};
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
    let root = $("nbPluginsV13");
    if (root) return root;
    root = document.createElement("section");
    root.id = "nbPluginsV13";
    root.className = "nb-p13";
    root.innerHTML = `
      <div class="nb-p13-head">
        <div><small>OPEN PLATFORM</small><h2>Plugins</h2><p id="nbP13Status">Loading…</p></div>
        <button id="nbP13Add" type="button">+ Install Manifest</button>
      </div>
      <form id="nbP13Form" class="ml-form card" hidden>
        <label>Plugin ID<input id="nbP13Id" required pattern="[A-Za-z0-9._-]+" maxlength="120"></label>
        <label>Name<input id="nbP13Name" required maxlength="120"></label>
        <label>Version<input id="nbP13Version" required value="1.0.0" maxlength="40"></label>
        <label>Permissions<input id="nbP13Permissions" placeholder="read_devices, control_devices"></label>
        <div class="ml-actions"><button type="submit">Install</button><button id="nbP13Cancel" type="button">Cancel</button></div>
      </form>
      <div id="nbP13Summary" class="nb-p13-summary"></div>
      <div id="nbP13List" class="nb-p13-list"></div>
    `;
    (document.querySelector("main.main") || document.querySelector("main") || document.body)
      .appendChild(root);
    $("nbP13Add").onclick = () => { $("nbP13Form").hidden = false; $("nbP13Id").focus(); };
    $("nbP13Cancel").onclick = () => { $("nbP13Form").hidden = true; };
    $("nbP13Form").onsubmit = install;
    $("nbP13List").onclick = action;
    return root;
  }

  async function load() {
    panel();
    try {
      const data = await api("/overview");
      state.plugins = data.plugins || [];
      $("nbP13Summary").innerHTML =
        `<span>${data.summary.installed} installed</span><span>${data.summary.enabled} enabled</span>`;
      $("nbP13List").innerHTML = state.plugins.length ? state.plugins.map(plugin => `
        <article data-plugin-id="${esc(plugin.id)}">
          <div><b>${esc(plugin.name)}</b><small>${esc(plugin.id)} · v${esc(plugin.version)}</small></div>
          <div class="ml-actions">
            <button data-action="toggle">${plugin.enabled ? "Disable" : "Enable"}</button>
            <button data-action="delete">Delete</button>
          </div>
        </article>
      `).join("") : `<div class="nb-p13-empty">No plugins installed.</div>`;
      $("nbP13Status").textContent = "Plugin platform ready";
    } catch (error) {
      $("nbP13Status").textContent = `Unavailable: ${error.message}`;
    }
  }

  async function install(event) {
    event.preventDefault();
    const permissions = $("nbP13Permissions").value.split(",").map(item => item.trim()).filter(Boolean);
    try {
      await api("/plugins", {
        method: "POST",
        body: JSON.stringify({
          id: $("nbP13Id").value.trim(),
          name: $("nbP13Name").value.trim(),
          version: $("nbP13Version").value.trim(),
          permissions
        })
      });
      $("nbP13Form").reset();
      $("nbP13Version").value = "1.0.0";
      $("nbP13Form").hidden = true;
      await load();
    } catch (error) {
      $("nbP13Status").textContent = `Install failed: ${error.message}`;
    }
  }

  async function action(event) {
    const button = event.target.closest("[data-action]");
    const id = button?.closest("[data-plugin-id]")?.dataset.pluginId;
    const plugin = state.plugins.find(item => String(item.id) === id);
    if (!button || !plugin) return;
    try {
      if (button.dataset.action === "toggle") {
        await api(`/plugins/${encodeURIComponent(id)}/enable`, {
          method: "POST",
          body: JSON.stringify({enabled: !plugin.enabled})
        });
      } else {
        if (!confirm(`Delete plugin \"${plugin.name}\"?`)) return;
        await api(`/plugins/${encodeURIComponent(id)}`, {method: "DELETE"});
      }
      await load();
    } catch (error) {
      $("nbP13Status").textContent = `${button.dataset.action} failed: ${error.message}`;
    }
  }

  function start() { panel(); load(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();

  window.NoorBrainPluginsV13 = Object.freeze({installed: true, version: "13.1.0", load, refresh: load});
})();
