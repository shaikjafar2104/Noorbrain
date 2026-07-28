(() => {
  "use strict";

  const API = "/api/activity";
  let refreshTimer = null;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function timeOnly(timestamp) {
    if (!timestamp) return "—";

    let value = timestamp;
    if (typeof timestamp === "number") {
      value = timestamp > 10_000_000_000 ? timestamp : timestamp * 1000;
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "—";

    return parsed.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
  }

  function iconFor(type) {
    const icons = {
      appeared: "👤",
      entered_zone: "➡️",
      moved_zone: "🔄",
      left_zone: "⬅️",
      stayed: "⏱️",
      disappeared: "👋",
      activity: "•"
    };
    return icons[type] || "•";
  }

  function addStyles() {
    if (document.getElementById("activityStyles")) return;

    const style = document.createElement("style");
    style.id = "activityStyles";
    style.textContent = `
      .activity-summary {
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:14px;
        margin-bottom:16px;
      }
      .activity-metric {
        padding:16px;
        border:1px solid rgba(255,255,255,.08);
        border-radius:12px;
        background:rgba(255,255,255,.025);
      }
      .activity-metric span {
        display:block;
        opacity:.68;
        font-size:.85rem;
        margin-bottom:7px;
      }
      .activity-metric strong { font-size:1.55rem; }
      .activity-row {
        display:grid;
        grid-template-columns:95px 42px 1fr;
        align-items:center;
        gap:10px;
        padding:13px 8px;
        border-bottom:1px solid rgba(255,255,255,.07);
      }
      .activity-row:last-child { border-bottom:0; }
      .activity-time {
        opacity:.62;
        font-variant-numeric:tabular-nums;
      }
      .activity-icon {
        font-size:1.15rem;
        text-align:center;
      }
      .activity-message { font-weight:600; }
      .activity-type {
        display:block;
        opacity:.55;
        font-size:.75rem;
        margin-top:3px;
      }
      .activity-empty {
        padding:38px 10px;
        text-align:center;
        opacity:.6;
      }
      .activity-toolbar {
        display:flex;
        gap:10px;
        align-items:center;
      }
      @media(max-width:650px) {
        .activity-row { grid-template-columns:72px 30px 1fr; }
      }
    `;
    document.head.appendChild(style);
  }

  function buildPage() {
    addStyles();

    const nav = document.getElementById("nav");
    if (nav && !nav.querySelector('[data-page="activity"]')) {
      const button = document.createElement("button");
      button.className = "nav-item";
      button.dataset.page = "activity";
      button.innerHTML = "🧠 <span>Activity</span>";

      const timelineButton = nav.querySelector('[data-page="timeline"]');
      if (timelineButton) nav.insertBefore(button, timelineButton);
      else nav.appendChild(button);

      button.addEventListener("click", openActivityPage);
    }

    if (!document.getElementById("page-activity")) {
      const main = document.querySelector("main.main");
      if (!main) return;

      const section = document.createElement("section");
      section.id = "page-activity";
      section.className = "page";
      section.innerHTML = `
        <article class="card">
          <div class="card-head">
            <div>
              <h2>Activity Monitor</h2>
              <p>Live person-aware events from NoorBrain</p>
            </div>
            <div class="activity-toolbar">
              <button id="activityRefresh" class="button secondary">Refresh</button>
              <button id="activityClear" class="button danger">Clear</button>
            </div>
          </div>
          <div class="activity-summary">
            <div class="activity-metric">
              <span>Active people</span>
              <strong id="activityActiveCount">0</strong>
            </div>
            <div class="activity-metric">
              <span>Recorded events</span>
              <strong id="activityEventCount">0</strong>
            </div>
            <div class="activity-metric">
              <span>Engine status</span>
              <strong id="activityStatus">—</strong>
            </div>
          </div>
          <div id="activityList" class="activity-empty">Waiting for activity…</div>
        </article>
      `;
      main.appendChild(section);

      document.getElementById("activityRefresh")
        ?.addEventListener("click", loadActivities);
      document.getElementById("activityClear")
        ?.addEventListener("click", clearActivities);
    }
  }

  function openActivityPage() {
    document.querySelectorAll(".page")
      .forEach(page => page.classList.remove("active"));

    document.querySelectorAll(".nav-item")
      .forEach(item => item.classList.toggle(
        "active",
        item.dataset.page === "activity"
      ));

    document.getElementById("page-activity")?.classList.add("active");

    const title = document.getElementById("pageTitle");
    const subtitle = document.getElementById("pageSubtitle");
    if (title) title.textContent = "Activity";
    if (subtitle) subtitle.textContent = "Live person movement and presence events";

    loadActivities();
    clearInterval(refreshTimer);
    refreshTimer = setInterval(loadActivities, 5000);
  }

  function eventMessage(event) {
    return (
      event.message ||
      event.description ||
      event.person_name ||
      event.event_type ||
      event.type ||
      "Activity event"
    );
  }

  async function loadActivities() {
    const list = document.getElementById("activityList");

    try {
      const response = await fetch(
        `${API}/activities?limit=100`,
        { cache: "no-store" }
      );

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const activeCount = data.active_count ?? data.active_people ?? 0;
      const eventCount = (
        data.event_count ??
        data.recorded_events ??
        data.total_events ??
        data.count ??
        0
      );
      const engineStatus = data.engine_status ?? data.engine ?? data.status ?? "running";
      const events = Array.isArray(data.events)
        ? data.events
        : Array.isArray(data.activities)
          ? data.activities
          : [];

      document.getElementById("activityActiveCount").textContent = activeCount;
      document.getElementById("activityEventCount").textContent = eventCount;
      document.getElementById("activityStatus").textContent = engineStatus;

      if (!events.length) {
        list.className = "activity-empty";
        list.textContent = "No activity events yet. Move in front of the camera.";
        return;
      }

      list.className = "";
      list.innerHTML = events.map(event => {
        const type = event.type || event.event_type || "activity";
        return `
          <div class="activity-row">
            <div class="activity-time">${escapeHtml(timeOnly(event.timestamp || event.created_at))}</div>
            <div class="activity-icon">${iconFor(type)}</div>
            <div>
              <div class="activity-message">${escapeHtml(eventMessage(event))}</div>
              <span class="activity-type">${escapeHtml(type)}</span>
            </div>
          </div>
        `;
      }).join("");
    } catch (error) {
      if (list) {
        list.className = "activity-empty";
        list.textContent = `Activity API unavailable: ${error.message}`;
      }
    }
  }

  async function clearActivities() {
    if (!confirm("Clear all activity events?")) return;

    try {
      const response = await fetch(`${API}/activities/clear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await loadActivities();
    } catch (error) {
      alert(`Unable to clear activities: ${error.message}`);
    }
  }

  document.addEventListener("click", event => {
    const navItem = event.target.closest(".nav-item");
    if (navItem && navItem.dataset.page !== "activity") {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildPage);
  } else {
    buildPage();
  }
})();
