(() => {
  "use strict";

  const API = "/api/vision-intelligence";
  const PAGE_ID = "page-vision-intelligence";
  const NAV_KEY = "vision-intelligence";

  function $(id) {
    return document.getElementById(id);
  }

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
    return (
      $("nav") ||
      document.querySelector(".sidebar nav") ||
      document.querySelector(".sidebar") ||
      document.querySelector("[data-navigation]") ||
      document.querySelector("aside")
    );
  }

  function findMain() {
    return (
      document.querySelector("main.main") ||
      document.querySelector("main") ||
      document.querySelector(".main") ||
      document.querySelector("#mainContent")
    );
  }

  function addStyles() {
    if ($("visionIntelligenceStyles")) return;

    const style = document.createElement("style");
    style.id = "visionIntelligenceStyles";
    style.textContent = `
      .vision-ai-grid {
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:12px;
      }
      .vision-ai-card {
        padding:14px;
        border:1px solid rgba(255,255,255,.08);
        border-radius:12px;
        background:rgba(255,255,255,.025);
      }
      .vision-ai-card span {
        display:block;
        opacity:.65;
        font-size:.8rem;
        margin-bottom:6px;
      }
      .vision-ai-card strong {
        font-size:1.4rem;
      }
      .vision-event-row {
        padding:12px 4px;
        border-bottom:1px solid rgba(255,255,255,.07);
      }
      .vision-event-row:last-child {
        border-bottom:0;
      }
      .vision-event-meta {
        opacity:.58;
        font-size:.78rem;
        margin-top:4px;
      }
    `;
    document.head.appendChild(style);
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

    if ($("pageTitle")) $("pageTitle").textContent = "Vision AI";
    if ($("pageSubtitle")) {
      $("pageSubtitle").textContent =
        "Live camera intelligence and event timeline";
    }

    load();
  }

  function ensureNav() {
    const nav = findNav();
    if (!nav) return false;

    if (!nav.querySelector(`[data-page="${NAV_KEY}"]`)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "nav-item";
      button.dataset.page = NAV_KEY;
      button.innerHTML = "👁️ <span>Vision AI</span>";
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
              <h2>Vision Intelligence</h2>
              <p>Live camera intelligence and event foundation</p>
            </div>
            <div>
              <button id="visionCapture" class="button success">Capture State</button>
              <button id="visionRefresh" class="button secondary">Refresh</button>
            </div>
          </div>
          <div id="visionMetrics" class="vision-ai-grid"></div>
        </article>

        <article class="card">
          <div class="card-head">
            <div>
              <h2>Recent Vision Events</h2>
              <p>Snapshots, detections and zones</p>
            </div>
          </div>
          <div id="visionEvents">No vision events yet.</div>
        </article>
      `;
      main.appendChild(page);

      $("visionCapture")?.addEventListener("click", capture);
      $("visionRefresh")?.addEventListener("click", load);
    }

    return true;
  }

  async function load() {
    const metrics = $("visionMetrics");
    const events = $("visionEvents");

    if (!metrics || !events) return;

    try {
      const [health, summary, recent] = await Promise.all([
        api("/health"),
        api("/summary"),
        api("/events?limit=50")
      ]);

      metrics.innerHTML = `
        <div class="vision-ai-card">
          <span>Service</span>
          <strong>${safe(health.status)}</strong>
        </div>
        <div class="vision-ai-card">
          <span>People detected</span>
          <strong>${safe(health.person_count ?? 0)}</strong>
        </div>
        <div class="vision-ai-card">
          <span>Vision FPS</span>
          <strong>${safe(health.fps ?? "—")}</strong>
        </div>
        <div class="vision-ai-card">
          <span>Stored events</span>
          <strong>${safe(summary.total_events ?? 0)}</strong>
        </div>
      `;

      events.innerHTML = recent.events?.length
        ? recent.events.map(event => `
            <div class="vision-event-row">
              <strong>${safe(event.message || event.event_type)}</strong>
              <div class="vision-event-meta">
                ${safe(event.created_at)} · ${safe(event.zone || "No zone")}
              </div>
            </div>
          `).join("")
        : "No vision events yet.";
    } catch (error) {
      metrics.textContent =
        `Vision Intelligence unavailable: ${error.message}`;
    }
  }

  async function capture() {
    try {
      await api("/snapshot");
      await load();
    } catch (error) {
      alert(`Capture failed: ${error.message}`);
    }
  }

  function mount() {
    addStyles();
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

    setTimeout(() => observer.disconnect(), 15000);
  }

  window.NoorBrainVisionAI = {
    open: openPage,
    refresh: load,
    mount
  };
})();
