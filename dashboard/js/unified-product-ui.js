(() => {
  "use strict";

  if (window.NoorBrainUnifiedUI?.installed) return;

  const featureMap = [
    {key: "ai", label: "AI & Routines", icon: "✦", ids: ["nbMobileAiCenterV8", "nbAiControlCenterV8"]},
    {key: "voice", label: "HALO Voice", icon: "◉", ids: ["nbVoicePlatformV9"]},
    {key: "home", label: "Home Devices", icon: "⌂", ids: ["nbWholeHomeV10"]},
    {key: "family", label: "Family", icon: "●", ids: ["nbFamilyV11"]},
    {key: "islamic", label: "Islamic", icon: "☾", ids: ["nbIslamicV12"]},
    {key: "plugins", label: "Plugins", icon: "◇", ids: ["nbPluginsV13"]},
    {key: "system", label: "System Health", icon: "✓", ids: ["nbReleaseV14"]},
  ];

  let collecting = false;
  let observerTimer = 0;

  function isMobilePage() {
    return location.pathname.startsWith("/mobile") || matchMedia("(max-width: 760px)").matches;
  }

  function ensureHub() {
    let hub = document.getElementById("nbUnifiedHub");
    if (hub) return hub;

    const host =
      document.querySelector(".mobile-main") ||
      document.querySelector("main") ||
      document.querySelector("#app") ||
      document.body;

    hub = document.createElement("section");
    hub.id = "nbUnifiedHub";
    hub.className = "nb-unified-hub";
    hub.innerHTML = `
      <div class="nb-uh-head">
        <div>
          <small>NOORBRAIN</small>
          <h2>Features</h2>
          <p>Everything in one clean place</p>
        </div>
        <button id="nbUhClose" type="button" hidden>Close</button>
      </div>
      <div id="nbUhMenu" class="nb-uh-menu"></div>
      <div id="nbUhStage" class="nb-uh-stage" hidden></div>
    `;

    const first = host.querySelector("section, .mobile-card, .card");
    if (first) first.insertAdjacentElement("beforebegin", hub);
    else host.appendChild(hub);

    const menu = hub.querySelector("#nbUhMenu");
    menu.innerHTML = featureMap.map(feature => `
      <button type="button" data-nb-feature="${feature.key}">
        <i>${feature.icon}</i>
        <span>${feature.label}</span>
        <b>›</b>
      </button>
    `).join("");

    menu.querySelectorAll("[data-nb-feature]").forEach(button => {
      button.addEventListener("click", () => openFeature(button.dataset.nbFeature));
    });
    hub.querySelector("#nbUhClose").addEventListener("click", closeFeature);
    return hub;
  }

  function choosePanel(feature) {
    const candidates = feature.ids
      .map(id => document.getElementById(id))
      .filter(Boolean);

    if (feature.key === "ai" && candidates.length > 1) {
      const preferredId = isMobilePage() ? "nbMobileAiCenterV8" : "nbAiControlCenterV8";
      const preferred = document.getElementById(preferredId);
      candidates.filter(item => item !== preferred).forEach(item => {
        item.classList.add("nb-unified-duplicate");
        item.hidden = true;
      });
      return preferred || candidates[0];
    }
    return candidates[0] || null;
  }

  function collectFeatures() {
    if (collecting) return;
    collecting = true;
    try {
      const hub = ensureHub();
      const stage = hub.querySelector("#nbUhStage");
      for (const feature of featureMap) {
        const panel = choosePanel(feature);
        const button = hub.querySelector(`[data-nb-feature="${feature.key}"]`);
        if (!panel) {
          button?.classList.add("is-unavailable");
          continue;
        }
        button?.classList.remove("is-unavailable");
        panel.dataset.nbUnifiedFeature = feature.key;
        panel.classList.add("nb-unified-panel");
        panel.hidden = hub.dataset.openFeature !== feature.key;
        if (panel.parentElement !== stage) stage.appendChild(panel);
      }

      const pluginTest = document.querySelector("#nbPluginsV13 #nbP13Add");
      if (pluginTest) pluginTest.hidden = true;

      const releaseHeading = document.querySelector("#nbReleaseV14 h2");
      if (releaseHeading) releaseHeading.textContent = "System Health";
      const releaseEyebrow = document.querySelector("#nbReleaseV14 small");
      if (releaseEyebrow) releaseEyebrow.textContent = "SYSTEM";

      const startup = document.getElementById("nbVpStartup");
      if (startup) {
        startup.checked = false;
        startup.disabled = true;
        startup.closest("label")?.classList.add("nb-electronic-voice-disabled");
      }
    } finally {
      collecting = false;
    }
  }

  function openFeature(key) {
    collectFeatures();
    const hub = ensureHub();
    const stage = hub.querySelector("#nbUhStage");
    const menu = hub.querySelector("#nbUhMenu");
    const close = hub.querySelector("#nbUhClose");
    const panel = stage.querySelector(`[data-nb-unified-feature="${key}"]`);
    if (!panel) return;

    stage.querySelectorAll(".nb-unified-panel").forEach(item => item.hidden = true);
    panel.hidden = false;
    stage.hidden = false;
    menu.hidden = true;
    close.hidden = false;
    hub.dataset.openFeature = key;
    hub.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function closeFeature() {
    const hub = ensureHub();
    hub.querySelector("#nbUhStage").hidden = true;
    hub.querySelector("#nbUhMenu").hidden = false;
    hub.querySelector("#nbUhClose").hidden = true;
    delete hub.dataset.openFeature;
  }

  function muteElectronicVoice() {
    const synth = window.speechSynthesis;
    if (!synth) return;
    try { synth.cancel(); } catch (_) {}

    const mutedSpeak = function () {
      try { synth.cancel(); } catch (_) {}
      window.dispatchEvent(new CustomEvent("noorbrain:electronic-voice-blocked"));
    };
    mutedSpeak.__noorbrainElectronicVoiceOff = true;

    try {
      if (!synth.speak?.__noorbrainElectronicVoiceOff) {
        Object.defineProperty(synth, "speak", {
          configurable: true,
          writable: true,
          value: mutedSpeak,
        });
      }
    } catch (_) {
      try { synth.speak = mutedSpeak; } catch (_) {}
    }
  }

  function start() {
    document.body.classList.add("nb-unified-ui-active");
    muteElectronicVoice();
    collectFeatures();

    const observer = new MutationObserver(() => {
      clearTimeout(observerTimer);
      observerTimer = window.setTimeout(collectFeatures, 100);
    });
    observer.observe(document.body, {childList: true, subtree: true});

    window.setTimeout(() => {
      muteElectronicVoice();
      collectFeatures();
    }, 500);
    window.setTimeout(() => {
      muteElectronicVoice();
      collectFeatures();
    }, 1800);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }

  window.NoorBrainUnifiedUI = Object.freeze({
    installed: true,
    version: "1.0.0",
    open: openFeature,
    close: closeFeature,
    refresh: collectFeatures,
    electronicVoice: "disabled",
  });
})();
