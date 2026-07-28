(() => {
  "use strict";

  const API = "/api/halo-brain";
  const PAGE_ID = "page-halo-brain";
  const NAV_KEY = "halo-brain";
  const $ = id => document.getElementById(id);

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    const body = await response.json();

    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return body;
  }

  function findNav() {
    return $("nav")
      || document.querySelector(".sidebar nav")
      || document.querySelector(".sidebar")
      || document.querySelector("[data-navigation]")
      || document.querySelector("aside");
  }

  function findMain() {
    return document.querySelector("main.main")
      || document.querySelector("main")
      || document.querySelector(".main")
      || document.querySelector("#mainContent");
  }

  function ensureNav() {
    const nav = findNav();
    if (!nav) return false;

    if (!nav.querySelector(`[data-page="${NAV_KEY}"]`)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "nav-item";
      button.dataset.page = NAV_KEY;
      button.innerHTML = "🧠 <span>HALO Brain</span>";
      button.addEventListener("click", openPage);
      nav.appendChild(button);
    }

    return true;
  }

  function ensurePage() {
    const main = findMain();
    if (!main) return false;

    if (!$(PAGE_ID)) {
      const page = document.createElement("section");
      page.id = PAGE_ID;
      page.className = "page";
      page.innerHTML = `
        <article class="card">
          <div class="card-head">
            <div>
              <h2>HALO Brain</h2>
              <p>Memory, context fusion, decisions and execution</p>
            </div>
            <button id="haloBrainRefresh" class="button secondary">Refresh</button>
          </div>
          <div id="haloBrainSummary">Loading…</div>
        </article>

        <article class="card">
          <h2>Brain Test</h2>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <input
              id="haloBrainText"
              style="min-width:300px;flex:1"
              value="What is the home status?"
            >
            <button id="haloBrainRun" class="button success">Run</button>
          </div>
          <pre id="haloBrainResult">Ready</pre>
        </article>

        <article class="card">
          <h2>Recent Decisions</h2>
          <div id="haloBrainDecisions">No decisions yet.</div>
        </article>
      `;
      main.appendChild(page);

      $("haloBrainRefresh")?.addEventListener("click", load);
      $("haloBrainRun")?.addEventListener("click", run);
    }

    return true;
  }

  function openPage() {
    document.querySelectorAll(".page")
      .forEach(page => page.classList.remove("active"));

    document.querySelectorAll(".nav-item")
      .forEach(item => item.classList.toggle(
        "active",
        item.dataset.page === NAV_KEY
      ));

    $(PAGE_ID)?.classList.add("active");

    if ($("pageTitle")) $("pageTitle").textContent = "HALO Brain";
    if ($("pageSubtitle")) {
      $("pageSubtitle").textContent =
        "Memory, decision-making and multimodal context";
    }

    load();
  }

  async function load() {
    try {
      const [health, decisions] = await Promise.all([
        api("/health"),
        api("/decisions?limit=20")
      ]);

      $("haloBrainSummary").textContent =
        `${health.memory_count} memories · ${health.decision_count} decisions · ${health.execution_count} executions`;

      $("haloBrainDecisions").innerHTML = decisions.decisions?.length
        ? decisions.decisions.map(item => `
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,.07)">
              <strong>${safe(item.signal)}</strong>
              <div style="opacity:.65;font-size:.8rem">
                ${safe(item.reason)} · ${safe(item.action?.kind)} / ${safe(item.action?.name)}
              </div>
            </div>
          `).join("")
        : "No decisions yet.";
    } catch (error) {
      $("haloBrainSummary").textContent =
        `HALO Brain unavailable: ${error.message}`;
    }
  }

  async function run() {
    const text = $("haloBrainText")?.value?.trim();

    if (!text) return;

    $("haloBrainResult").textContent = "Thinking…";

    try {
      const result = await api("/process", {
        method: "POST",
        body: JSON.stringify({
          text,
          session_id: "halo-brain-dashboard",
          confirm: false
        })
      });

      $("haloBrainResult").textContent =
        JSON.stringify(result, null, 2);

      await load();
    } catch (error) {
      $("haloBrainResult").textContent =
        `Brain error: ${error.message}`;
    }
  }

  function mount() {
    return ensureNav() && ensurePage();
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

  window.NoorBrainHALOBrain = {
    open: openPage,
    refresh: load,
    mount
  };
})();
