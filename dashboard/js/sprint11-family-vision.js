(() => {
  "use strict";
  if (window.NoorBrainFamilyV11?.installed) return;

  const API = "/api/family-intelligence-v11";
  const state = {members: [], presence: {}, editing: null};
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
    let root = $("nbFamilyV11");
    if (root) return root;
    root = document.createElement("section");
    root.id = "nbFamilyV11";
    root.className = "nb-family-v11";
    root.innerHTML = `
      <div class="nb-f11-head">
        <div><small>FAMILY AI</small><h2>Family & Presence</h2><p id="nbF11Status">Loading…</p></div>
        <button id="nbF11Add" type="button">+ Add Member</button>
      </div>
      <form id="nbF11Form" class="ml-form card" hidden>
        <label>Name<input id="nbF11Name" required maxlength="120"></label>
        <label>Role<input id="nbF11Role" required maxlength="80" value="family"></label>
        <div class="ml-actions"><button type="submit">Save</button><button id="nbF11Cancel" type="button">Cancel</button></div>
      </form>
      <div id="nbF11Summary" class="nb-f11-summary"></div>
      <div id="nbF11Members" class="nb-f11-grid"></div>
      <label class="nb-f11-private"><input id="nbF11Recognition" type="checkbox"><span>Face recognition enabled</span></label>
    `;
    (document.querySelector("main.main") || document.querySelector("main") || document.body)
      .appendChild(root);
    $("nbF11Add").onclick = () => editor();
    $("nbF11Cancel").onclick = closeEditor;
    $("nbF11Form").onsubmit = save;
    $("nbF11Members").onclick = action;
    $("nbF11Recognition").onchange = event => privacy(event.target.checked);
    return root;
  }

  async function load() {
    panel();
    try {
      const data = await api("/overview");
      state.members = data.members || [];
      state.presence = data.presence || {};
      const summary = data.summary || {};
      $("nbF11Summary").innerHTML =
        `<span>${summary.members || 0} members</span><span>${summary.present || 0} present</span>` +
        `<span>${summary.rooms_active || 0} rooms active</span><span>${summary.unknown_present || 0} unknown</span>`;
      $("nbF11Recognition").checked = Boolean(data.privacy?.recognition_enabled);
      $("nbF11Members").innerHTML = state.members.length ? state.members.map(member => {
        const presence = state.presence[member.id];
        return `<article class="${presence?.present ? "is-present" : ""}" data-member-id="${esc(member.id)}">
          <div>${esc(member.name).slice(0, 1).toUpperCase()}</div>
          <strong>${esc(member.name)}</strong>
          <span>${presence?.present ? `In ${esc(presence.room)}` : "Away"}</span>
          <small>${esc(member.role)}</small>
          <div class="ml-actions"><button data-action="edit">Edit</button><button data-action="delete">Delete</button></div>
        </article>`;
      }).join("") : `<div class="nb-f11-empty">No family members configured.</div>`;
      $("nbF11Status").textContent = "Family intelligence ready";
    } catch (error) {
      $("nbF11Status").textContent = `Unavailable: ${error.message}`;
    }
  }

  function editor(member = null) {
    state.editing = member?.id || null;
    $("nbF11Name").value = member?.name || "";
    $("nbF11Role").value = member?.role || "family";
    $("nbF11Form").hidden = false;
    $("nbF11Name").focus();
  }

  function closeEditor() {
    state.editing = null;
    $("nbF11Form").hidden = true;
  }

  async function save(event) {
    event.preventDefault();
    try {
      await api(state.editing ? `/members/${encodeURIComponent(state.editing)}` : "/members", {
        method: state.editing ? "PATCH" : "POST",
        body: JSON.stringify({name: $("nbF11Name").value.trim(), role: $("nbF11Role").value.trim()})
      });
      closeEditor();
      await load();
    } catch (error) {
      $("nbF11Status").textContent = `Save failed: ${error.message}`;
    }
  }

  async function action(event) {
    const button = event.target.closest("[data-action]");
    const id = button?.closest("[data-member-id]")?.dataset.memberId;
    const member = state.members.find(item => String(item.id) === id);
    if (!button || !member) return;
    if (button.dataset.action === "edit") return editor(member);
    if (!confirm(`Delete \"${member.name}\"?`)) return;
    try {
      await api(`/members/${encodeURIComponent(id)}`, {method: "DELETE"});
      await load();
    } catch (error) {
      $("nbF11Status").textContent = `Delete failed: ${error.message}`;
    }
  }

  async function privacy(enabled) {
    try {
      await api("/privacy", {method: "PATCH", body: JSON.stringify({recognition_enabled: enabled})});
      await load();
    } catch (error) {
      $("nbF11Status").textContent = `Privacy update failed: ${error.message}`;
    }
  }

  function start() { panel(); load(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();

  window.NoorBrainFamilyV11 = Object.freeze({installed: true, version: "11.1.0", load, refresh: load});
})();
