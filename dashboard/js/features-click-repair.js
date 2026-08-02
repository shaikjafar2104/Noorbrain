(() => {
  "use strict";

  if (window.NoorBrainFeatureClickRepair?.installed) return;

  const panels = {
    ai: ["nbMobileAiCenterV8", "nbAiControlCenterV8"],
    voice: ["nbVoicePlatformV9"],
    home: ["nbWholeHomeV10"],
    family: ["nbFamilyV11"],
    islamic: ["nbIslamicV12"],
    plugins: ["nbPluginsV13"],
    system: ["nbReleaseV14"],
  };

  function mobile() {
    return location.pathname.startsWith("/mobile") ||
      matchMedia("(max-width: 760px)").matches;
  }

  function hubParts() {
    const hub = document.getElementById("nbUnifiedHub");
    return {
      hub,
      menu: hub?.querySelector("#nbUhMenu"),
      stage: hub?.querySelector("#nbUhStage"),
      close: hub?.querySelector("#nbUhClose"),
    };
  }

  function findPanel(key) {
    const ids = panels[key] || [];
    if (key === "ai") {
      const preferred = document.getElementById(
        mobile() ? "nbMobileAiCenterV8" : "nbAiControlCenterV8"
      );
      if (preferred) return preferred;
    }
    for (const id of ids) {
      const element = document.getElementById(id);
      if (element) return element;
    }
    return null;
  }

  function showMessage(stage, message) {
    let notice = document.getElementById("nbFeatureRepairNotice");
    if (!notice) {
      notice = document.createElement("div");
      notice.id = "nbFeatureRepairNotice";
      notice.className = "nb-feature-repair-notice";
      stage.appendChild(notice);
    }
    notice.textContent = message;
    notice.hidden = false;
  }

  function open(key, retry = true) {
    window.NoorBrainUnifiedUI?.refresh?.();
    const {hub, menu, stage, close} = hubParts();
    if (!hub || !menu || !stage || !close) return false;

    let panel = findPanel(key);
    if (!panel && retry) {
      showMessage(stage, "Loading feature…");
      stage.hidden = false;
      menu.hidden = true;
      close.hidden = false;
      window.setTimeout(() => open(key, false), 350);
      return true;
    }

    if (!panel) {
      showMessage(stage, "This feature is not installed yet.");
      stage.hidden = false;
      menu.hidden = true;
      close.hidden = false;
      return false;
    }

    const notice = document.getElementById("nbFeatureRepairNotice");
    if (notice) notice.hidden = true;

    if (panel.parentElement !== stage) stage.appendChild(panel);

    stage.querySelectorAll(".nb-unified-panel, [data-nb-unified-feature]")
      .forEach(item => {
        item.hidden = true;
        item.style.setProperty("display", "none", "important");
      });

    panel.dataset.nbUnifiedFeature = key;
    panel.classList.add("nb-unified-panel");
    panel.classList.remove("nb-production-hidden", "nb-unified-duplicate");
    panel.removeAttribute("aria-hidden");
    panel.hidden = false;
    panel.style.setProperty("display", "block", "important");

    stage.hidden = false;
    stage.style.setProperty("display", "block", "important");
    menu.hidden = true;
    menu.style.setProperty("display", "none", "important");
    close.hidden = false;
    close.style.removeProperty("display");
    hub.dataset.openFeature = key;

    window.setTimeout(() => {
      panel.scrollIntoView({behavior: "smooth", block: "start"});
    }, 40);
    return true;
  }

  function close() {
    const {hub, menu, stage, close: closeButton} = hubParts();
    if (!hub || !menu || !stage || !closeButton) return;

    stage.querySelectorAll(".nb-unified-panel, [data-nb-unified-feature]")
      .forEach(item => {
        item.hidden = true;
        item.style.setProperty("display", "none", "important");
      });

    stage.hidden = true;
    stage.style.setProperty("display", "none", "important");
    menu.hidden = false;
    menu.style.removeProperty("display");
    closeButton.hidden = true;
    closeButton.style.setProperty("display", "none", "important");
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

    const closeButton = event.target.closest?.("#nbUhClose");
    if (closeButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      close();
    }
  }

  document.addEventListener("click", handleClick, true);
  document.addEventListener("touchend", event => {
    const button = event.target.closest?.("[data-nb-feature], #nbUhClose");
    if (!button) return;
    event.preventDefault();
    if (button.matches("#nbUhClose")) close();
    else open(button.dataset.nbFeature);
  }, {capture: true, passive: false});

  window.NoorBrainFeatureClickRepair = Object.freeze({
    installed: true,
    version: "1.0.0",
    open,
    close,
  });
})();
