(() => {
  "use strict";

  const API = "/api/personalized-halo";
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json"
      },
      ...options
    });

    const body = await response.json();

    if (!response.ok) {
      throw new Error(
        body.detail || `HTTP ${response.status}`
      );
    }

    return body;
  }

  function host() {
    return (
      document.getElementById("page-halo")
      || document.querySelector("main.main")
      || document.querySelector("main")
    );
  }

  function ensurePanel() {
    const target = host();

    if (!target) return false;

    if (!$("personalizedHaloPanel")) {
      const panel = document.createElement("section");
      panel.id = "personalizedHaloPanel";
      panel.className = "card";
      panel.innerHTML = `
        <div class="card-head">
          <div>
            <h2>Personalized HALO</h2>
            <p>Family-aware greetings and context</p>
          </div>
          <button id="personalizedHaloRefresh" class="button secondary">
            Refresh
          </button>
        </div>

        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">
          <input id="personalizedHaloPerson" placeholder="Face person ID">
          <input id="personalizedHaloZone" value="Hall" placeholder="Zone">
          <button id="personalizedHaloCompose" class="button secondary">
            Compose
          </button>
          <button id="personalizedHaloGreet" class="button success">
            Greet
          </button>
        </div>

        <div id="personalizedHaloSummary">Loading…</div>
        <pre id="personalizedHaloResult">Ready</pre>
        <div id="personalizedHaloEvents">No greetings yet.</div>
      `;

      target.appendChild(panel);

      $("personalizedHaloRefresh")
        ?.addEventListener("click", load);

      $("personalizedHaloCompose")
        ?.addEventListener(
          "click",
          () => run(false),
        );

      $("personalizedHaloGreet")
        ?.addEventListener(
          "click",
          () => run(true),
        );
    }

    return true;
  }

  async function run(greet) {
    const personId =
      $("personalizedHaloPerson")
        ?.value
        ?.trim();

    if (!personId) {
      alert("Enter a Face person ID.");
      return;
    }

    try {
      const result = await api(
        greet ? "/greet" : "/compose",
        {
          method: "POST",
          body: JSON.stringify({
            person_id: personId,
            zone:
              $("personalizedHaloZone")
                ?.value
                ?.trim()
              || null,
            force: greet
          })
        }
      );

      $("personalizedHaloResult").textContent =
        JSON.stringify(
          result,
          null,
          2
        );

      await load();
    } catch (error) {
      $("personalizedHaloResult").textContent =
        `Personalized HALO failed: ${error.message}`;
    }
  }

  async function load() {
    try {
      const [health, events] =
        await Promise.all([
          api("/health"),
          api("/events?limit=30")
        ]);

      $("personalizedHaloSummary").textContent =
        `${health.event_count} personalized greetings · `
        + `${health.enabled ? "Enabled" : "Disabled"}`;

      $("personalizedHaloEvents").innerHTML =
        events.events?.length
          ? events.events.map(event => `
              <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.07)">
                <strong>${event.profile_name || event.profile_id}</strong><br>
                <small>
                  ${event.created_at} ·
                  ${event.zone || "No zone"} ·
                  ${event.period}
                </small>
              </div>
            `).join("")
          : "No greetings yet.";
    } catch (error) {
      $("personalizedHaloSummary").textContent =
        `Personalized HALO unavailable: ${error.message}`;
    }
  }

  function mount() {
    const ready = ensurePanel();

    if (ready) load();

    return ready;
  }

  if (!mount()) {
    const observer =
      new MutationObserver(() => {
        if (mount()) {
          observer.disconnect();
        }
      });

    observer.observe(
      document.documentElement,
      {
        childList: true,
        subtree: true
      }
    );

    setTimeout(
      () => observer.disconnect(),
      20000
    );
  }

  window.NoorBrainPersonalizedHALO = {
    mount,
    refresh: load
  };
})();
