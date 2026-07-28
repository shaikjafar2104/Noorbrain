(() => {
  "use strict";

  const API = "/api/vision-zones";
  const PAGE_ID = "page-vision-zones";
  const NAV_KEY = "vision-zones";

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
    if ($("visionZonesStyles")) return;

    const style = document.createElement("style");
    style.id = "visionZonesStyles";
    style.textContent = `
      .vision-zone-form {
        display:grid;
        gap:10px;
        margin-bottom:16px;
      }
      .vision-zone-form input,
      .vision-zone-form textarea {
        width:100%;
      }
      .vision-zone-row,
      .vision-motion-row {
        padding:12px 4px;
        border-bottom:1px solid rgba(255,255,255,.07);
      }
      .vision-zone-row:last-child,
      .vision-motion-row:last-child {
        border-bottom:0;
      }
      .vision-zone-row {
        display:flex;
        justify-content:space-between;
        gap:12px;
        align-items:center;
      }
      .vision-zone-delete {
        border:0;
        border-radius:10px;
        padding:8px 11px;
        cursor:pointer;
        background:rgba(239,68,68,.16);
        color:#fca5a5;
      }
      .vision-zone-meta {
        opacity:.6;
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

    if ($("pageTitle")) $("pageTitle").textContent = "Vision Zones";
    if ($("pageSubtitle")) {
      $("pageSubtitle").textContent =
        "Zone-aware motion tracking";
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
      button.innerHTML = "🗺️ <span>Vision Zones</span>";
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
              <h2>Vision Zones</h2>
              <p>Create normalized camera zones</p>
            </div>
            <button id="visionZonesRefresh" class="button secondary">Refresh</button>
          </div>

          <div class="vision-zone-form">
            <input id="visionZoneName" placeholder="Zone name" value="Hall">
            <textarea id="visionZonePoints" rows="4">[
  {"x":0.05,"y":0.05},
  {"x":0.95,"y":0.05},
  {"x":0.95,"y":0.95},
  {"x":0.05,"y":0.95}
]</textarea>
            <button id="visionZoneCreate" class="button success">Create Zone</button>
          </div>

          <div id="visionZoneList">No zones yet.</div>
        </article>

        <article class="card">
          <div class="card-head">
            <div>
              <h2>Motion Timeline</h2>
              <p>Latest zone-aware motion samples</p>
            </div>
          </div>
          <div id="visionMotionList">No motion events yet.</div>
        </article>
      `;
      main.appendChild(page);

      $("visionZonesRefresh")?.addEventListener("click", load);
      $("visionZoneCreate")?.addEventListener("click", createZone);
    }

    return true;
  }

  async function createZone() {
    const name = $("visionZoneName")?.value?.trim();

    try {
      const points = JSON.parse(
        $("visionZonePoints")?.value || "[]"
      );

      await api("/zones", {
        method: "POST",
        body: JSON.stringify({
          name,
          camera_id: "primary",
          points,
          enabled: true
        })
      });

      await load();
    } catch (error) {
      alert(`Zone create failed: ${error.message}`);
    }
  }

  async function deleteZone(zoneId, zoneName) {
    const confirmed = confirm(
      `Delete Vision Zone "${zoneName}"?`
    );

    if (!confirmed) return;

    try {
      await api(`/zones/${encodeURIComponent(zoneId)}`, {
        method: "DELETE"
      });

      await load();
    } catch (error) {
      alert(`Zone delete failed: ${error.message}`);
    }
  }

  async function load() {
    const zoneList = $("visionZoneList");
    const motionList = $("visionMotionList");

    if (!zoneList || !motionList) return;

    try {
      const [zones, motion] = await Promise.all([
        api("/zones"),
        api("/motion?limit=50")
      ]);

      zoneList.innerHTML = zones.zones?.length
        ? zones.zones.map(zone => `
            <div class="vision-zone-row">
              <div>
                <strong>${safe(zone.name)}</strong>
                <div class="vision-zone-meta">
                  ${safe(zone.camera_id)} ·
                  ${safe(zone.points?.length || 0)} points
                </div>
              </div>
              <button
                type="button"
                class="vision-zone-delete"
                data-zone-id="${safe(zone.id)}"
                data-zone-name="${safe(zone.name)}"
              >
                Delete
              </button>
            </div>
          `).join("")
        : "No zones yet.";

      zoneList
        .querySelectorAll(".vision-zone-delete")
        .forEach(button => {
          button.addEventListener("click", () => {
            deleteZone(
              button.dataset.zoneId,
              button.dataset.zoneName
            );
          });
        });

      motionList.innerHTML = motion.events?.length
        ? motion.events.map(event => `
            <div class="vision-motion-row">
              <strong>${safe(event.zone_name || "Unassigned")}</strong>
              <div class="vision-zone-meta">
                ${safe(event.created_at)} ·
                confidence ${safe(event.confidence)}
              </div>
            </div>
          `).join("")
        : "No motion events yet.";
    } catch (error) {
      zoneList.textContent =
        `Vision Zones unavailable: ${error.message}`;
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

  window.NoorBrainVisionZones = {
    open: openPage,
    refresh: load,
    mount
  };
})();
