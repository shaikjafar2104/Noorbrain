(() => {
  "use strict";

  const API = "/api/face-identity";
  const PAGE_ID = "page-face-identity";
  const NAV_KEY = "face-identity";
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
      button.innerHTML = "🙂 <span>Face Identity</span>";
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
              <h2>Face Registration</h2>
              <p>Create family identities and enrollment profiles</p>
            </div>
            <button id="faceRefresh" class="button secondary">Refresh</button>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <input id="facePersonName" placeholder="Person name">
            <button id="facePersonCreate" class="button success">Register Person</button>
          </div>
          <div id="faceSummary" style="margin-top:14px">Loading…</div>
        </article>

        <article class="card">
          <h2>Registered People</h2>
          <div id="facePersons">No registered people.</div>
        </article>

        <article class="card">
          <h2>Recognition Timeline</h2>
          <div id="faceEvents">No recognition events.</div>
        </article>
      `;
      main.appendChild(page);

      $("faceRefresh")?.addEventListener("click", load);
      $("facePersonCreate")?.addEventListener("click", createPerson);
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

    if ($("pageTitle")) $("pageTitle").textContent = "Face Identity";
    if ($("pageSubtitle")) {
      $("pageSubtitle").textContent =
        "Face registration and recognition foundation";
    }

    load();
  }

  async function createPerson() {
    const name = $("facePersonName")?.value?.trim();

    if (!name) return;

    try {
      await api("/persons", {
        method: "POST",
        body: JSON.stringify({ name })
      });

      $("facePersonName").value = "";
      await load();
    } catch (error) {
      alert(`Registration failed: ${error.message}`);
    }
  }

  async function deletePerson(personId, name) {
    if (!confirm(`Delete face identity "${name}"?`)) return;

    try {
      await api(`/persons/${encodeURIComponent(personId)}`, {
        method: "DELETE"
      });
      await load();
    } catch (error) {
      alert(`Delete failed: ${error.message}`);
    }
  }

  async function load() {
    try {
      const [summary, persons, events] = await Promise.all([
        api("/summary"),
        api("/persons"),
        api("/events?limit=50")
      ]);

      $("faceSummary").textContent =
        `${summary.person_count} people · ${summary.sample_count} samples · ${summary.recognition_event_count} recognition events`;

      $("facePersons").innerHTML = persons.persons?.length
        ? persons.persons.map(person => `
            <div style="display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.07)">
              <div>
                <strong>${safe(person.name)}</strong>
                <div style="opacity:.65;font-size:.8rem">
                  ${safe(person.sample_count)} enrollment sample(s)
                </div>
              </div>
              <button
                class="button danger face-delete"
                data-id="${safe(person.id)}"
                data-name="${safe(person.name)}"
              >Delete</button>
            </div>
          `).join("")
        : "No registered people.";

      $("facePersons")
        .querySelectorAll(".face-delete")
        .forEach(button => {
          button.addEventListener("click", () => {
            deletePerson(button.dataset.id, button.dataset.name);
          });
        });

      $("faceEvents").innerHTML = events.events?.length
        ? events.events.map(event => `
            <div style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,.07)">
              <strong>${event.recognized ? safe(event.person_name) : "Unknown"}</strong>
              <div style="opacity:.65;font-size:.8rem">
                ${safe(event.created_at)} · confidence ${safe(event.confidence)}
              </div>
            </div>
          `).join("")
        : "No recognition events.";
    } catch (error) {
      $("faceSummary").textContent =
        `Face Identity unavailable: ${error.message}`;
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

  window.NoorBrainFaceIdentity = {
    open: openPage,
    refresh: load,
    mount
  };
})();
