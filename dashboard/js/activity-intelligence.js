(() => {
  "use strict";

  const API = "/api/activity-intelligence";
  const PAGE_ID = "page-activity-intelligence";
  const NAV_KEY = "activity-intelligence";
  const $ = id => document.getElementById(id);

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function api(path) {
    const response = await fetch(API + path, {
      cache: "no-store"
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

  function addStyles() {
    if ($("activityIntelligenceStyles")) return;

    const style = document.createElement("style");
    style.id = "activityIntelligenceStyles";
    style.textContent = `
      .activity-ai-grid {
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:12px;
      }
      .activity-ai-card {
        padding:14px;
        border:1px solid rgba(255,255,255,.08);
        border-radius:12px;
        background:rgba(255,255,255,.025);
      }
      .activity-ai-row {
        padding:10px 0;
        border-bottom:1px solid rgba(255,255,255,.07);
      }
      .activity-ai-row:last-child {
        border-bottom:0;
      }
      .activity-ai-meta {
        opacity:.62;
        font-size:.78rem;
        margin-top:4px;
      }
      .activity-ai-filter {
        display:flex;
        gap:10px;
        flex-wrap:wrap;
        margin-bottom:14px;
      }
      .activity-ai-filter input,
      .activity-ai-filter select {
        min-width:160px;
      }
      .activity-heatmap {
        display:grid;
        grid-template-columns:90px repeat(24, minmax(16px, 1fr));
        gap:3px;
        overflow-x:auto;
      }
      .activity-heat-cell {
        min-width:16px;
        height:16px;
        border-radius:3px;
        background:rgba(90,174,255,.12);
      }
    `;
    document.head.appendChild(style);
  }

  function ensureNav() {
    const nav = findNav();
    if (!nav) return false;

    if (!nav.querySelector(`[data-page="${NAV_KEY}"]`)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "nav-item";
      button.dataset.page = NAV_KEY;
      button.innerHTML = "📊 <span>Activity Intelligence</span>";
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
              <h2>Activity Intelligence</h2>
              <p>Vision, presence and face activity analytics</p>
            </div>
            <div>
              <a class="button secondary" href="${API}/export?format=csv&days=30">CSV</a>
              <a class="button secondary" href="${API}/export?format=json&days=30">JSON</a>
              <button id="activityAIRefresh" class="button success">Refresh</button>
            </div>
          </div>
          <div id="activityAISummary" class="activity-ai-grid"></div>
        </article>

        <article class="card">
          <div class="card-head">
            <div>
              <h2>Activity Search</h2>
              <p>Filter recent activity events</p>
            </div>
          </div>
          <div class="activity-ai-filter">
            <input id="activityAIQuery" placeholder="Search">
            <input id="activityAIZone" placeholder="Zone">
            <select id="activityAIDays">
              <option value="1">Today</option>
              <option value="7">7 days</option>
              <option value="30" selected>30 days</option>
              <option value="90">90 days</option>
            </select>
            <button id="activityAISearch" class="button secondary">Search</button>
          </div>
          <div id="activityAIEvents">No events.</div>
        </article>

        <article class="card">
          <h2>Weekly Heatmap</h2>
          <div id="activityAIHeatmap">Loading…</div>
        </article>
      `;
      main.appendChild(page);

      $("activityAIRefresh")?.addEventListener("click", load);
      $("activityAISearch")?.addEventListener("click", loadEvents);
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

    if ($("pageTitle")) {
      $("pageTitle").textContent = "Activity Intelligence";
    }

    if ($("pageSubtitle")) {
      $("pageSubtitle").textContent =
        "Timeline, reports, heatmaps and exports";
    }

    load();
  }

  function selectedDays() {
    return Number($("activityAIDays")?.value || 30);
  }

  async function load() {
    await Promise.all([
      loadSummary(),
      loadEvents(),
      loadHeatmap()
    ]);
  }

  async function loadSummary() {
    try {
      const summary = await api(
        `/summary?days=${selectedDays()}`
      );

      $("activityAISummary").innerHTML = `
        <div class="activity-ai-card">
          <span>Total events</span>
          <strong>${safe(summary.total_events)}</strong>
        </div>
        <div class="activity-ai-card">
          <span>Entries</span>
          <strong>${safe(summary.entry_count)}</strong>
        </div>
        <div class="activity-ai-card">
          <span>Exits</span>
          <strong>${safe(summary.exit_count)}</strong>
        </div>
        <div class="activity-ai-card">
          <span>Active zones</span>
          <strong>${safe(Object.keys(summary.by_zone || {}).length)}</strong>
        </div>
      `;
    } catch (error) {
      $("activityAISummary").textContent =
        `Activity Intelligence unavailable: ${error.message}`;
    }
  }

  async function loadEvents() {
    const days = selectedDays();
    const query = encodeURIComponent(
      $("activityAIQuery")?.value?.trim() || ""
    );
    const zone = encodeURIComponent(
      $("activityAIZone")?.value?.trim() || ""
    );

    try {
      const result = await api(
        `/events?days=${days}&limit=200&query=${query}&zone=${zone}`
      );

      $("activityAIEvents").innerHTML = result.events?.length
        ? result.events.map(event => `
            <div class="activity-ai-row">
              <strong>${safe(event.message || event.event_type)}</strong>
              <div class="activity-ai-meta">
                ${safe(event.created_at)} ·
                ${safe(event.zone || "No zone")} ·
                ${safe(event.event_type)}
              </div>
            </div>
          `).join("")
        : "No events.";
    } catch (error) {
      $("activityAIEvents").textContent =
        `Search failed: ${error.message}`;
    }
  }

  async function loadHeatmap() {
    try {
      const result = await api(
        `/heatmap?days=${selectedDays()}`
      );

      let html = '<div class="activity-heatmap">';

      result.weekdays.forEach((day, dayIndex) => {
        html += `<div>${safe(day.slice(0, 3))}</div>`;

        for (let hour = 0; hour < 24; hour += 1) {
          const value =
            result.matrix[String(dayIndex)][String(hour)] || 0;
          const opacity = Math.min(
            0.12 + value * 0.12,
            0.95
          );

          html += `
            <div
              class="activity-heat-cell"
              title="${safe(day)} ${hour}:00 · ${value} events"
              style="background:rgba(90,174,255,${opacity})"
            ></div>
          `;
        }
      });

      html += "</div>";
      $("activityAIHeatmap").innerHTML = html;
    } catch (error) {
      $("activityAIHeatmap").textContent =
        `Heatmap unavailable: ${error.message}`;
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

    setTimeout(() => observer.disconnect(), 20000);
  }

  window.NoorBrainActivityIntelligence = {
    open: openPage,
    refresh: load,
    mount
  };
})();
