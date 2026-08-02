(() => {
  "use strict";

  if (window.NoorBrainSprint6Release) return;

  const API = "/api/product-release-v6";
  const state = {
    diagnostics: null,
    settings: null,
    backups: [],
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

  function bytes(value) {
    const numeric = Number(value || 0);

    if (numeric < 1024) return `${numeric} B`;
    if (numeric < 1024 ** 2) return `${(numeric / 1024).toFixed(1)} KB`;
    if (numeric < 1024 ** 3) return `${(numeric / 1024 ** 2).toFixed(1)} MB`;
    return `${(numeric / 1024 ** 3).toFixed(1)} GB`;
  }

  function mount() {
    const modules =
      document.querySelector(".nbv2-module-section")
      || document.querySelector("#nbv2Modules")
      || document.querySelector("main");

    if (!modules || $("nbs6Release")) return;

    const panel = document.createElement("section");
    panel.id = "nbs6Release";
    panel.className = "nbs6-panel";

    panel.innerHTML = `
      <article class="nbs6-card">
        <div class="nbs6-head">
          <div>
            <small>SPRINT 6</small>
            <h2>Product Release</h2>
          </div>
          <div class="nbs6-actions">
            <button class="nbs6-button" id="nbs6SelfCheck">Self Check</button>
            <button class="nbs6-button primary" id="nbs6Backup">Create Backup</button>
          </div>
        </div>

        <div class="nbs6-release-banner">
          <div>
            <small>NOORBRAIN PRODUCT</small>
            <h3>Release 6.0</h3>
            <span>Mobile, Vision, Smart Home, HALO AI and Islamic Center</span>
          </div>
          <div class="nbs6-release-badge" id="nbs6ReleaseBadge">CHECKING</div>
        </div>

        <div class="nbs6-grid" id="nbs6Metrics"></div>
        <p class="nbs6-status" id="nbs6Status">Loading product diagnostics…</p>
      </article>

      <article class="nbs6-card">
        <div class="nbs6-head">
          <div>
            <small>HEALTH</small>
            <h2>System Checks</h2>
          </div>
          <div class="nbs6-actions">
            <button class="nbs6-button" id="nbs6Refresh">↻ Refresh</button>
          </div>
        </div>
        <div class="nbs6-grid" id="nbs6Checks"></div>
      </article>

      <article class="nbs6-card">
        <div class="nbs6-head">
          <div>
            <small>APPEARANCE</small>
            <h2>Product Settings</h2>
          </div>
          <div class="nbs6-actions">
            <button class="nbs6-button primary" id="nbs6Save">Save</button>
          </div>
        </div>

        <div class="nbs6-settings">
          <label>
            Release channel
            <select id="nbs6Channel">
              <option value="stable">Stable</option>
              <option value="beta">Beta</option>
              <option value="developer">Developer</option>
            </select>
          </label>

          <label>
            Theme
            <select id="nbs6Theme">
              <option value="system">System</option>
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </label>

          <label>
            Compact mode
            <select id="nbs6Compact">
              <option value="false">Off</option>
              <option value="true">On</option>
            </select>
          </label>

          <label>
            Animations
            <select id="nbs6Animations">
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </label>
        </div>
      </article>

      <article class="nbs6-card">
        <div class="nbs6-head">
          <div>
            <small>RECOVERY</small>
            <h2>Backups</h2>
          </div>
        </div>
        <div class="nbs6-backup-list" id="nbs6Backups"></div>
      </article>
    `;

    modules.insertAdjacentElement("afterend", panel);

    bind();

    Promise.allSettled([
      loadDiagnostics(),
      loadSettings(),
      loadBackups(),
    ]);
  }

  function bind() {
    $("nbs6Refresh").onclick = loadDiagnostics;
    $("nbs6SelfCheck").onclick = selfCheck;
    $("nbs6Backup").onclick = createBackup;
    $("nbs6Save").onclick = saveSettings;
  }

  async function loadDiagnostics() {
    try {
      const data = await request(`${API}/diagnostics`);
      state.diagnostics = data;
      renderDiagnostics();

      $("nbs6Status").textContent =
        `${data.system.platform} · Python ${data.system.python}`;

      $("nbs6ReleaseBadge").textContent = "READY";
    } catch (error) {
      $("nbs6Status").textContent = error.message;
      $("nbs6ReleaseBadge").textContent = "ERROR";
    }
  }

  function renderDiagnostics() {
    const data = state.diagnostics;

    $("nbs6Metrics").innerHTML = `
      <article class="nbs6-metric">
        <span>Data</span>
        <b>${bytes(data.storage.data_bytes)}</b>
      </article>
      <article class="nbs6-metric">
        <span>Dashboard</span>
        <b>${bytes(data.storage.dashboard_bytes)}</b>
      </article>
      <article class="nbs6-metric">
        <span>Services</span>
        <b>${bytes(data.storage.services_bytes)}</b>
      </article>
      <article class="nbs6-metric">
        <span>Free storage</span>
        <b>${bytes(data.storage.free_bytes)}</b>
      </article>
    `;

    $("nbs6Checks").innerHTML = Object.entries(data.checks)
      .map(([name, result]) => `
        <article class="nbs6-check ${result.present ? "ok" : "bad"}">
          <span>${safe(name)}</span>
          <b>${result.present ? "PASS" : "MISSING"}</b>
        </article>
      `)
      .join("");
  }

  async function loadSettings() {
    try {
      const data = await request(`${API}/settings`);
      state.settings = data.settings;

      $("nbs6Channel").value = data.settings.release_channel || "stable";
      $("nbs6Theme").value = data.settings.theme || "system";
      $("nbs6Compact").value = String(data.settings.compact_mode === true);
      $("nbs6Animations").value = String(data.settings.animations !== false);

      applySettings(data.settings);
    } catch (error) {
      $("nbs6Status").textContent = error.message;
    }
  }

  function applySettings(settings) {
    document.body.classList.toggle(
      "nbs6-compact",
      settings.compact_mode === true
    );

    document.body.classList.toggle(
      "nbs6-no-animations",
      settings.animations === false
    );

    if (settings.theme === "dark") {
      document.documentElement.style.colorScheme = "dark";
    } else if (settings.theme === "light") {
      document.documentElement.style.colorScheme = "light";
    } else {
      document.documentElement.style.colorScheme = "";
    }
  }

  async function saveSettings() {
    try {
      const data = await request(`${API}/settings`, {
        method: "POST",
        body: JSON.stringify({
          release_channel: $("nbs6Channel").value,
          theme: $("nbs6Theme").value,
          compact_mode: $("nbs6Compact").value === "true",
          animations: $("nbs6Animations").value === "true",
        }),
      });

      state.settings = data.settings;
      applySettings(data.settings);
      $("nbs6Status").textContent = "Product settings saved.";
    } catch (error) {
      $("nbs6Status").textContent = error.message;
    }
  }

  async function selfCheck() {
    try {
      const data = await request(`${API}/self-check`, {
        method: "POST",
        body: "{}",
      });

      $("nbs6ReleaseBadge").textContent =
        data.status === "pass" ? "READY" : "WARNING";

      $("nbs6Status").textContent =
        data.status === "pass"
          ? "All NoorBrain product checks passed."
          : `Missing: ${data.failed.join(", ")}`;

      await loadDiagnostics();
    } catch (error) {
      $("nbs6Status").textContent = error.message;
    }
  }

  async function createBackup() {
    $("nbs6Status").textContent = "Creating product backup…";

    try {
      const data = await request(`${API}/backup`, {
        method: "POST",
        body: "{}",
      });

      $("nbs6Status").textContent =
        `Backup created: ${data.filename} (${bytes(data.size_bytes)})`;

      await loadBackups();
    } catch (error) {
      $("nbs6Status").textContent = error.message;
    }
  }

  async function loadBackups() {
    try {
      const data = await request(`${API}/backups`);
      state.backups = data.backups;
      renderBackups();
    } catch (error) {
      $("nbs6Status").textContent = error.message;
    }
  }

  function renderBackups() {
    const host = $("nbs6Backups");

    if (!state.backups.length) {
      host.innerHTML = `
        <div class="nbs6-empty">
          No product backups yet.
        </div>
      `;
      return;
    }

    host.innerHTML = state.backups.map(backup => `
      <article class="nbs6-backup">
        <div>
          <b>${safe(backup.name)}</b>
          <small>${bytes(backup.size_bytes)} · ${safe(backup.modified)}</small>
        </div>
        <div class="nbs6-actions">
          <a class="nbs6-button" href="${safe(backup.download)}">Download</a>
          <button class="nbs6-button danger" data-delete-backup="${safe(backup.name)}">Delete</button>
        </div>
      </article>
    `).join("");

    host.querySelectorAll("[data-delete-backup]").forEach(button => {
      button.onclick = () => deleteBackup(button.dataset.deleteBackup);
    });
  }

  async function deleteBackup(filename) {
    try {
      await request(`${API}/backups/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });

      await loadBackups();
      $("nbs6Status").textContent = "Backup deleted.";
    } catch (error) {
      $("nbs6Status").textContent = error.message;
    }
  }

  window.NoorBrainSprint6Release = {
    version: "6.0.0",
    loadDiagnostics,
    selfCheck,
    createBackup,
    loadBackups,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
