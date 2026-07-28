(() => {
  "use strict";

  const API = "/api/habit-learning";
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json"},
      ...options
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function findInsightsPage() {
    return (
      document.querySelector('[data-page="ai-insights"]')
      || document.querySelector('[data-page="insights"]')
    );
  }

  function findMain() {
    return document.querySelector("main.main")
      || document.querySelector("main")
      || document.querySelector(".main");
  }

  function ensurePanel() {
    const main = findMain();
    if (!main) return false;

    if (!$("habitLearningPanel")) {
      const panel = document.createElement("section");
      panel.id = "habitLearningPanel";
      panel.className = "card";
      panel.innerHTML = `
        <div class="card-head">
          <div>
            <h2>Habit Learning</h2>
            <p>Routine patterns and proactive suggestions</p>
          </div>
          <div>
            <button id="habitImport" class="button secondary">Import Activity</button>
            <button id="habitRebuild" class="button secondary">Rebuild</button>
            <button id="habitGenerate" class="button success">Generate</button>
          </div>
        </div>
        <div id="habitSummary">Loading…</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:14px">
          <div>
            <h3>Patterns</h3>
            <div id="habitPatterns">No patterns.</div>
          </div>
          <div>
            <h3>Suggestions</h3>
            <div id="habitSuggestions">No suggestions.</div>
          </div>
        </div>
      `;
      main.appendChild(panel);

      $("habitImport")?.addEventListener("click", async () => {
        await api("/import-activity?days=30", {method:"POST"});
        await load();
      });

      $("habitRebuild")?.addEventListener("click", async () => {
        await api("/patterns/rebuild", {method:"POST"});
        await load();
      });

      $("habitGenerate")?.addEventListener("click", async () => {
        await api("/suggestions/generate", {method:"POST"});
        await load();
      });
    }
    return true;
  }

  async function load() {
    try {
      const [health, patterns, suggestions] = await Promise.all([
        api("/health"),
        api("/patterns?limit=50"),
        api("/suggestions?limit=50")
      ]);

      $("habitSummary").textContent =
        `${health.observation_count} observations · ${health.pattern_count} patterns · ${health.suggestion_count} suggestions`;

      $("habitPatterns").innerHTML = patterns.patterns?.length
        ? patterns.patterns.map(item =>
            `<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,.07)">
              <strong>${item.description}</strong><br>
              <small>${Math.round((item.confidence || 0) * 100)}% confidence</small>
            </div>`
          ).join("")
        : "No patterns.";

      $("habitSuggestions").innerHTML = suggestions.suggestions?.length
        ? suggestions.suggestions.map(item =>
            `<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,.07)">
              <strong>${item.message}</strong><br>
              <small>${item.status}</small>
            </div>`
          ).join("")
        : "No suggestions.";
    } catch (error) {
      $("habitSummary").textContent = `Habit Learning unavailable: ${error.message}`;
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
    observer.observe(document.documentElement, {childList:true, subtree:true});
    setTimeout(() => observer.disconnect(), 20000);
  }

  window.NoorBrainHabitLearning = {mount, refresh: load};
})();
