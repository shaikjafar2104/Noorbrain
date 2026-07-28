(() => {
  "use strict";

  const API = "/api/prayer-intelligence";
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json"},
      ...options
    });

    const body = await response.json();

    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return body;
  }

  function host() {
    return (
      document.getElementById("page-reminder-rules")
      || document.getElementById("page-reminders")
      || document.querySelector("main.main")
      || document.querySelector("main")
    );
  }

  function ensurePanel() {
    const target = host();
    if (!target) return false;

    if (!$("prayerIntelligencePanel")) {
      const panel = document.createElement("section");
      panel.id = "prayerIntelligencePanel";
      panel.className = "card";
      panel.innerHTML = `
        <div class="card-head">
          <div>
            <h2>Prayer Intelligence</h2>
            <p>Prayer times, Adhan reminders and Islamic modes</p>
          </div>
          <button id="prayerRefresh" class="button secondary">Refresh</button>
        </div>

        <div id="prayerNext">Loading…</div>
        <div id="prayerTimes" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:14px"></div>

        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px">
          <button id="prayerTest" class="button success">Test Voice</button>
          <button id="prayerRamadan" class="button secondary">Toggle Ramadan</button>
        </div>
      `;
      target.appendChild(panel);

      $("prayerRefresh")?.addEventListener("click", load);
      $("prayerTest")?.addEventListener("click", async () => {
        await api("/test", {
          method: "POST",
          body: JSON.stringify({prayer: "maghrib"})
        });
      });

      $("prayerRamadan")?.addEventListener("click", async () => {
        const current = await api("/settings");
        await api("/settings", {
          method: "PATCH",
          body: JSON.stringify({
            ramadan_mode: !current.settings.ramadan_mode
          })
        });
        await load();
      });
    }

    return true;
  }

  async function load() {
    try {
      const [status, settings] = await Promise.all([
        api("/status"),
        api("/settings")
      ]);

      const next = new Date(status.next_time);
      $("prayerNext").innerHTML = `
        <strong>Next: ${status.next_prayer.toUpperCase()}</strong>
        <div>${next.toLocaleString()}</div>
        <small>
          ${status.today.friday_mode ? "Jummah mode · " : ""}
          ${settings.settings.ramadan_mode ? "Ramadan mode" : "Normal mode"}
        </small>
      `;

      const names = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"];

      $("prayerTimes").innerHTML = names.map(name => {
        const value = new Date(status.today.times[name]);
        return `
          <div style="padding:12px;border:1px solid rgba(255,255,255,.08);border-radius:12px">
            <strong>${name.toUpperCase()}</strong><br>
            <span>${value.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</span>
          </div>
        `;
      }).join("");
    } catch (error) {
      $("prayerNext").textContent =
        `Prayer Intelligence unavailable: ${error.message}`;
    }
  }

  function mount() {
    const ready = ensurePanel();
    if (ready) load();
    return ready;
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

  window.NoorBrainPrayerIntelligence = {
    mount,
    refresh: load
  };
})();
