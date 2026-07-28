(() => {
  "use strict";

  const API = "/api/halo-action-planner";

  function byId(id) {
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

  function buildPage() {
    const nav = byId("nav");

    if (nav && !nav.querySelector('[data-page="action-planner"]')) {
      const button = document.createElement("button");
      button.className = "nav-item";
      button.dataset.page = "action-planner";
      button.innerHTML = "🧩 <span>Action Planner</span>";
      nav.appendChild(button);
      button.addEventListener("click", openPage);
    }

    if (!byId("page-action-planner")) {
      const main = document.querySelector("main.main");
      if (!main) return;

      const page = document.createElement("section");
      page.id = "page-action-planner";
      page.className = "page";
      page.innerHTML = `
        <article class="card">
          <div class="card-head">
            <div>
              <h2>HALO Action Planner</h2>
              <p>Plan and inspect multi-step commands</p>
            </div>
            <button id="plannerRefresh" class="button secondary">Refresh</button>
          </div>
          <div class="planner-form">
            <input id="plannerText" value="Home status and camera status">
            <button id="plannerCreate" class="button success">Create Plan</button>
          </div>
          <pre id="plannerResult">Ready</pre>
        </article>

        <article class="card">
          <div class="card-head">
            <div>
              <h2>Recent Plans</h2>
              <p>Execution and confirmation history</p>
            </div>
          </div>
          <div id="plannerList">No plans yet.</div>
        </article>
      `;
      main.appendChild(page);

      byId("plannerCreate")?.addEventListener("click", createPlan);
      byId("plannerRefresh")?.addEventListener("click", loadPlans);
    }

    addStyles();
  }

  function addStyles() {
    if (byId("haloPlannerStyles")) return;

    const style = document.createElement("style");
    style.id = "haloPlannerStyles";
    style.textContent = `
      .planner-form {
        display:flex;
        gap:10px;
        flex-wrap:wrap;
      }
      .planner-form input {
        min-width:280px;
        flex:1;
      }
      #plannerResult {
        margin-top:14px;
        white-space:pre-wrap;
      }
      .planner-card {
        padding:14px;
        border:1px solid rgba(255,255,255,.08);
        border-radius:12px;
        margin-bottom:10px;
      }
      .planner-card h3 {
        margin:0 0 8px;
      }
      .planner-step {
        opacity:.75;
        margin-top:4px;
      }
    `;
    document.head.appendChild(style);
  }

  async function createPlan() {
    const result = byId("plannerResult");
    const text = byId("plannerText")?.value?.trim();

    if (!text) return;

    try {
      const data = await api("/plan", {
        method: "POST",
        body: JSON.stringify({
          text,
          session_id: "dashboard-action-planner"
        })
      });

      result.textContent = JSON.stringify(data, null, 2);
      await loadPlans();
    } catch (error) {
      result.textContent = `Planner error: ${error.message}`;
    }
  }

  async function loadPlans() {
    const list = byId("plannerList");

    try {
      const data = await api("/plans");

      if (!data.plans?.length) {
        list.textContent = "No plans yet.";
        return;
      }

      list.innerHTML = data.plans.slice(0, 20).map(plan => `
        <div class="planner-card">
          <h3>${safe(plan.original_text)}</h3>
          <div>Status: ${safe(plan.execution?.status || plan.status)}</div>
          ${(plan.steps || []).map(step => `
            <div class="planner-step">
              ${safe(step.index + 1)}. ${safe(step.kind)} → ${safe(step.name)}
            </div>
          `).join("")}
        </div>
      `).join("");
    } catch (error) {
      list.textContent = `Planner unavailable: ${error.message}`;
    }
  }

  function openPage() {
    document.querySelectorAll(".page")
      .forEach(page => page.classList.remove("active"));

    document.querySelectorAll(".nav-item")
      .forEach(item => item.classList.toggle(
        "active",
        item.dataset.page === "action-planner"
      ));

    byId("page-action-planner")?.classList.add("active");

    if (byId("pageTitle")) byId("pageTitle").textContent = "Action Planner";
    if (byId("pageSubtitle")) byId("pageSubtitle").textContent = "HALO multi-step planning and execution";

    loadPlans();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildPage);
  } else {
    buildPage();
  }
})();
