(() => {
  "use strict";

  const API = "/api/halo-voice-runtime";
  const PAGE_ID = "page-voice-runtime";
  const NAV_KEY = "voice-runtime";

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

  function badge(status) {
    const normalized = String(status || "unknown").toLowerCase();
    const good = ["healthy", "ready", "running", "ok"].includes(normalized);

    return `
      <span class="halo-runtime-badge ${good ? "good" : "warn"}">
        ${safe(status || "unknown")}
      </span>
    `;
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
    if ($("haloVoiceRuntimeStyles")) return;

    const style = document.createElement("style");
    style.id = "haloVoiceRuntimeStyles";
    style.textContent = `
      .halo-runtime-grid {
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:12px;
      }
      .halo-runtime-card {
        padding:14px;
        border:1px solid rgba(255,255,255,.08);
        border-radius:12px;
        background:rgba(255,255,255,.025);
      }
      .halo-runtime-card h3 {
        margin:0 0 8px;
        font-size:.95rem;
      }
      .halo-runtime-badge {
        display:inline-block;
        padding:4px 9px;
        border-radius:999px;
        font-size:.75rem;
      }
      .halo-runtime-badge.good {
        background:rgba(34,197,94,.16);
        color:#86efac;
      }
      .halo-runtime-badge.warn {
        background:rgba(245,158,11,.16);
        color:#fcd34d;
      }
      .halo-runtime-test {
        display:flex;
        gap:10px;
        flex-wrap:wrap;
      }
      .halo-runtime-test input {
        min-width:280px;
        flex:1;
      }
      #voiceRuntimeResult {
        margin-top:14px;
        white-space:pre-wrap;
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

    if ($("pageTitle")) $("pageTitle").textContent = "Voice Runtime";
    if ($("pageSubtitle")) {
      $("pageSubtitle").textContent =
        "HALO audio intelligence and streaming speech";
    }

    loadStatus();
  }

  function ensureNav() {
    const nav = findNav();
    if (!nav) return false;

    if (!nav.querySelector(`[data-page="${NAV_KEY}"]`)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "nav-item";
      button.dataset.page = NAV_KEY;
      button.innerHTML = "🎙️ <span>HALO Speak</span>";
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
              <h2>HALO Speak</h2>
              <p>Wake word, VAD, STT, TTS and audio health</p>
            </div>
            <button id="voiceRuntimeRefresh" class="button secondary">Refresh</button>
          </div>
          <div id="voiceRuntimeSummary" class="halo-runtime-grid"></div>
        </article>

        <article class="card">
          <div class="card-head">
            <div>
              <h2>Speech Test</h2>
              <p>Queue an offline HALO response</p>
            </div>
          </div>
          <div class="halo-runtime-test">
            <input
              id="voiceRuntimeText"
              value="Assalamu Alaikum. HALO Voice Runtime is ready."
            >
            <button id="voiceRuntimeSpeak" class="button success">Speak</button>
            <button id="voiceRuntimeInterrupt" class="button danger">Interrupt</button>
          </div>
          <pre id="voiceRuntimeResult">Ready</pre>
        </article>
      `;
      main.appendChild(page);

      $("voiceRuntimeRefresh")?.addEventListener("click", loadStatus);
      $("voiceRuntimeSpeak")?.addEventListener("click", speak);
      $("voiceRuntimeInterrupt")?.addEventListener("click", interrupt);
    }

    return true;
  }

  async function loadStatus() {
    const summary = $("voiceRuntimeSummary");
    if (!summary) return;

    try {
      const data = await api("/status");
      const components = data.components || {};

      summary.innerHTML = Object.entries(components)
        .map(([name, value]) => `
          <div class="halo-runtime-card">
            <h3>${safe(name)}</h3>
            ${badge(value?.status)}
          </div>
        `)
        .join("");
    } catch (error) {
      summary.textContent =
        `Voice Runtime unavailable: ${error.message}`;
    }
  }

  async function speak() {
    const result = $("voiceRuntimeResult");
    const text = $("voiceRuntimeText")?.value?.trim();

    if (!text) return;

    try {
      const data = await api("/tts/speak", {
        method: "POST",
        body: JSON.stringify({
          text,
          priority: 10
        })
      });

      result.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      result.textContent = `Speak error: ${error.message}`;
    }
  }

  async function interrupt() {
    const result = $("voiceRuntimeResult");

    try {
      const data = await api("/tts/interrupt", {
        method: "POST",
        body: "{}"
      });

      result.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
      result.textContent =
        `Interrupt error: ${error.message}`;
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

  window.NoorBrainHALOSpeak = {
    open: openPage,
    refresh: loadStatus,
    mount
  };
})();
