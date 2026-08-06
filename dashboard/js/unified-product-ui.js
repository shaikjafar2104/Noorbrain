(() => {
  "use strict";

  if (window.NoorBrainUnifiedUI?.installed) return;

  const features = [
    {key: "ai", label: "AI & Routines", icon: "✦", ids: ["nbMobileAiCenterV8", "nbAiControlCenterV8", "nbs8a1Decision", "nbs8bRoutine"]},
    {key: "voice", label: "HALO Voice", icon: "◉", ids: ["nbVoicePlatformV9"]},
    {key: "home", label: "Home Devices", icon: "⌂", ids: ["nbWholeHomeV10", "nbs3SmartHome", "nbs7DeviceEcosystem"]},
    {key: "family", label: "Family", icon: "●", ids: ["nbFamilyV11"]},
    {key: "islamic", label: "Islamic", icon: "☾", ids: ["nbIslamicV12", "nbs5IslamicCenter"]},
    {key: "plugins", label: "Plugins", icon: "◇", ids: ["nbPluginsV13"]},
    {key: "system", label: "System Health", icon: "✓", ids: ["nbReleaseV14", "nbs6Release"]},
  ];

  const moduleFeature = {
    devices: "home",
    automation: "ai",
    habits: "ai",
    insights: "ai",
    prayer: "islamic",
    reminders: "islamic",
    family: "family",
    voice: "voice",
    settings: "system",
  };

  const studioTargets = {
    vision: "/studio#vision",
    zones: "/studio#zones",
    presence: "/studio#presence",
    faces: "/studio#gallery",
    rules: "/studio#reminder-rules",
    notifications: "/studio#notifications",
    media: "/studio#media-library",
  };

  function ensureHub() {
    let hub = document.getElementById("nbUnifiedHub");
    if (hub) return hub;

    hub = document.createElement("section");
    hub.id = "nbUnifiedHub";
    hub.className = "nb-unified-hub";
    hub.innerHTML = `
      <div class="nb-uh-head">
        <div><small>NOORBRAIN</small><h2>Features</h2><p>Everything in one clean place</p></div>
        <button id="nbUhClose" type="button" hidden>← Features</button>
      </div>
      <div id="nbUhMenu" class="nb-uh-menu">
        ${features.map(item => `
          <button type="button" data-nb-feature="${item.key}">
            <i>${item.icon}</i><span>${item.label}</span><b>›</b>
          </button>`).join("")}
      </div>
      <div id="nbUhStage" class="nb-uh-stage" hidden></div>`;

    const main = document.querySelector("main") || document.body;
    const hero = document.querySelector(".nbv2-hero");
    if (hero) hero.insertAdjacentElement("afterend", hub);
    else main.prepend(hub);
    return hub;
  }

  function allPanels(feature) {
    return feature.ids.map(id => document.getElementById(id)).filter(Boolean);
  }

  function collect() {
    const hub = ensureHub();
    const stage = hub.querySelector("#nbUhStage");

    for (const feature of features) {
      const panels = allPanels(feature);
      const button = hub.querySelector(`[data-nb-feature="${feature.key}"]`);
      button?.classList.toggle("is-unavailable", panels.length === 0);
      for (const panel of panels) {
        panel.dataset.nbUnifiedFeature = feature.key;
        panel.classList.add("nb-unified-panel");
        if (panel.parentElement !== stage) stage.appendChild(panel);
        panel.hidden = true;
      }
    }

    document.querySelector("#nbPluginsV13 #nbP13Add")?.setAttribute("hidden", "");
    const startup = document.getElementById("nbVpStartup");
    if (startup) {
      startup.checked = false;
      startup.disabled = true;
      startup.closest("label")?.classList.add("nb-electronic-voice-disabled");
    }
  }

  function open(key) {
    collect();
    const hub = ensureHub();
    const stage = hub.querySelector("#nbUhStage");
    const panels = [...stage.querySelectorAll(`[data-nb-unified-feature="${key}"]`)];
    if (!panels.length) return false;

    stage.querySelectorAll("[data-nb-unified-feature]").forEach(panel => {
      panel.hidden = true;
    });
    panels.forEach(panel => { panel.hidden = false; });
    stage.hidden = false;
    hub.querySelector("#nbUhMenu").hidden = true;
    hub.querySelector("#nbUhClose").hidden = false;
    hub.dataset.openFeature = key;
    hub.scrollIntoView({behavior: "smooth", block: "start"});
    return true;
  }

  function close() {
    const hub = ensureHub();
    hub.querySelectorAll("[data-nb-unified-feature]").forEach(panel => {
      panel.hidden = true;
    });
    hub.querySelector("#nbUhStage").hidden = true;
    hub.querySelector("#nbUhMenu").hidden = false;
    hub.querySelector("#nbUhClose").hidden = true;
    delete hub.dataset.openFeature;
    hub.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function handleClick(event) {
    const featureButton = event.target.closest?.("[data-nb-feature]");
    if (featureButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      open(featureButton.dataset.nbFeature);
      return;
    }

    if (event.target.closest?.("#nbUhClose")) {
      event.preventDefault();
      event.stopImmediatePropagation();
      close();
      return;
    }

    const moduleButton = event.target.closest?.("[data-module]");
    if (!moduleButton) return;
    const module = moduleButton.dataset.module;

    if (module === "vision") {
      event.preventDefault();
      event.stopImmediatePropagation();
      document.getElementById("nbv2CameraSection")?.scrollIntoView({behavior: "smooth"});
      return;
    }

    if (moduleFeature[module]) {
      event.preventDefault();
      event.stopImmediatePropagation();
      open(moduleFeature[module]);
      return;
    }

    if (studioTargets[module]) {
      event.preventDefault();
      event.stopImmediatePropagation();
      location.href = studioTargets[module];
    }
  }

  async function enforceProductAudio() {
    const requests = [
      fetch("/api/voice-platform-v9/config", {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({startup_speech: false}),
      }),
      fetch("/api/dual-audio-v15/config", {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({input_mode: "both", output_mode: "both", app_audio: true, pi_audio: true}),
      }),
      fetch("/api/audio-camera-rules-v15/config", {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          camera_triggered_audio: true,
          raspberry_pi_speaker: true,
          app_speaker: true,
          adhan_media_audio: true,
          halo_natural_voice: false,
        }),
      }),
    ];
    await Promise.allSettled(requests);
  }

  function start() {
    document.body.classList.add("nb-unified-ui-active");
    document.addEventListener("click", handleClick, true);
    collect();
    window.setTimeout(collect, 250);
    window.setTimeout(collect, 1000);
    window.setTimeout(enforceProductAudio, 300);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }

  window.NoorBrainUnifiedUI = Object.freeze({
    installed: true,
    version: "16.0.0",
    open,
    close,
    refresh: collect,
    electronicVoice: "disabled",
    cameraMode: "single-clean-feed",
  });
})();
