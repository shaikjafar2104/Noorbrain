(() => {
  "use strict";

  const API = "/api/person-presence";
  const PAGE_ID = "page-person-presence";
  const NAV_KEY = "person-presence";
  const $ = id => document.getElementById(id);

  async function api(path) {
    const response = await fetch(API + path, { cache: "no-store" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
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

  function openPage() {
    document.querySelectorAll(".page").forEach(page => page.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(item => {
      item.classList.toggle("active", item.dataset.page === NAV_KEY);
    });

    $(PAGE_ID)?.classList.add("active");
    if ($("pageTitle")) $("pageTitle").textContent = "Person Presence";
    if ($("pageSubtitle")) $("pageSubtitle").textContent = "Track IDs, zones, entry and exit events";
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
      button.innerHTML = "🚶 <span>Person Presence</span>";
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
              <h2>Person Presence</h2>
              <p>Active person tracks and zone occupancy</p>
            </div>
            <button id="presenceRefresh" class="button secondary">Refresh</button>
          </div>
          <div id="presenceMetrics">Loading…</div>
        </article>

        <article class="card">
          <h2>Active Tracks</h2>
          <div id="presenceTracks">No active tracks.</div>
        </article>

        <article class="card">
          <h2>Presence Timeline</h2>
          <div id="presenceEvents">No events yet.</div>
        </article>
      `;
      main.appendChild(page);
      $("presenceRefresh")?.addEventListener("click", load);
    }

    return true;
  }

  async function load() {
    try {
      const [summary, timeline] = await Promise.all([
        api("/tracks"),
        api("/events?limit=50")
      ]);

      $("presenceMetrics").textContent =
        `${summary.active_count || 0} active · ${Object.keys(summary.by_zone || {}).length} occupied zones`;

      $("presenceTracks").innerHTML = summary.tracks?.length
        ? summary.tracks.map(track =>
            `<div><strong>Track ${track.track_id}</strong> — ${track.zone || "Unassigned"}</div>`
          ).join("")
        : "No active tracks.";

      $("presenceEvents").innerHTML = timeline.events?.length
        ? timeline.events.map(event =>
            `<div><strong>${event.message || event.event_type}</strong><br><small>${event.created_at}</small></div>`
          ).join("")
        : "No events yet.";
    } catch (error) {
      $("presenceMetrics").textContent = `Unavailable: ${error.message}`;
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

  window.NoorBrainPersonPresence = { open: openPage, refresh: load, mount };
})();
