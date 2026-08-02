(() => {
  "use strict";

  if (window.NoorBrainMobileDuplicateHaloClickFix) return;

  const VERSION = "1.0.0";
  const bound = new WeakSet();

  function visible(element) {
    if (!element) return false;
    const style = getComputedStyle(element);
    return style.display !== "none"
      && style.visibility !== "hidden"
      && style.opacity !== "0";
  }

  function removeDuplicateHalo() {
    const candidates = [
      "#nbHaloMic",
      "#nbUniversalMic",
      "#nbVoiceOfflineMic",
      "[data-nb-final-mic='true']",
      "[data-action='halo']",
      ".nb-mobile-halo-main",
      ".nb-mobile-profile",
    ];

    const nodes = [];
    candidates.forEach(selector => {
      document.querySelectorAll(selector).forEach(node => {
        if (!nodes.includes(node) && visible(node)) nodes.push(node);
      });
    });

    const preferred =
      document.querySelector(".nb-mobile-halo-main")
      || document.querySelector("#nbUniversalMic")
      || document.querySelector("[data-nb-final-mic='true']")
      || document.querySelector("#nbHaloMic")
      || nodes[0];

    nodes.forEach(node => {
      if (node === preferred) return;

      if (
        node.closest(".nb-mobile-home-nav")
        || node.classList.contains("nb-mobile-profile")
      ) {
        node.dataset.nbHaloProxy = "true";
        node.classList.remove("nb-hidden-halo");
        return;
      }

      node.classList.add("nb-hidden-halo");
      node.setAttribute("aria-hidden", "true");
      node.tabIndex = -1;
    });

    if (preferred) {
      preferred.dataset.nbPrimaryHalo = "true";
      preferred.classList.remove("nb-hidden-halo");
      preferred.removeAttribute("aria-hidden");
    }
  }

  function primaryHalo() {
    return document.querySelector("[data-nb-primary-halo='true']")
      || document.querySelector(".nb-mobile-halo-main")
      || document.querySelector("#nbUniversalMic")
      || document.querySelector("[data-nb-final-mic='true']")
      || document.querySelector("#nbHaloMic");
  }

  function triggerHalo() {
    const target = primaryHalo();
    if (!target) return;

    if (target.matches(".nb-mobile-halo-main")) {
      const actual =
        document.querySelector("#nbUniversalMic")
        || document.querySelector("[data-nb-final-mic='true']")
        || document.querySelector("#nbHaloMic");

      if (actual && actual !== target) {
        actual.click();
        return;
      }
    }

    target.click();
  }

  function addDevice() {
    if (
      window.NoorBrainHaloOneClick
      && typeof window.NoorBrainHaloOneClick.openDeviceModal === "function"
    ) {
      window.NoorBrainHaloOneClick.openDeviceModal();
      return;
    }

    const button = document.querySelector(
      "#nbAddDevice, #nbMobileAddFirstDevice, [data-add-device]"
    );

    if (button) button.click();
  }

  function scrollToSection(selector) {
    const target = document.querySelector(selector);
    if (!target) return;
    target.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function sendHaloCommand(command) {
    if (
      window.NoorBrainHaloOneClick
      && typeof window.NoorBrainHaloOneClick.sendCommand === "function"
    ) {
      window.NoorBrainHaloOneClick.sendCommand(command);
      return;
    }

    const input = document.querySelector("#nbHaloInput");
    if (input) input.value = command;
    document.querySelector("#nbHaloSend")?.click();
  }

  function perform(action) {
    const actions = {
      home: () => window.scrollTo({top: 0, behavior: "smooth"}),
      devices: addDevice,
      halo: triggerHalo,
      vision: () => scrollToSection("#nbMobileCameraCard"),
      camera: () => scrollToSection("#nbMobileCameraCard"),
      more: () => scrollToSection(".nb-mobile-essential-grid"),
      prayer: () => sendHaloCommand("What is the next prayer?"),
      reminders: () => sendHaloCommand("Show my reminders"),
      family: () => sendHaloCommand("Who is at home?"),
      automation: () => sendHaloCommand("Show my automations"),
    };

    actions[action]?.();
  }

  function bindButton(button) {
    if (!button || bound.has(button)) return;
    bound.add(button);

    button.style.pointerEvents = "auto";
    button.style.touchAction = "manipulation";
    button.style.position = button.style.position || "relative";
    button.style.zIndex = button.style.zIndex || "10";

    button.addEventListener("click", event => {
      const action =
        button.dataset.action
        || button.dataset.mobileTab
        || button.dataset.nbHaloProxy;

      if (!action) return;

      event.preventDefault();
      event.stopPropagation();

      if (button.dataset.nbHaloProxy === "true") {
        perform("halo");
      } else {
        perform(action);
      }
    }, true);
  }

  function repairClicks() {
    document.querySelectorAll(
      "[data-action], [data-mobile-tab], [data-nb-halo-proxy='true']"
    ).forEach(bindButton);

    document.querySelectorAll(
      ".nb-mobile-room-card, .nb-mobile-device, "
      + ".nb-mobile-essential-grid button, "
      + ".nb-mobile-quick-grid button, "
      + ".nb-mobile-home-nav button, "
      + ".nb-mobile-section-head button"
    ).forEach(button => {
      button.style.pointerEvents = "auto";
      button.style.touchAction = "manipulation";
      button.style.position = button.style.position || "relative";
      button.style.zIndex = "10";
    });

    document.querySelectorAll(
      ".nb-mobile-home-center::before, .nb-mobile-home-center::after"
    );
  }

  function install() {
    removeDuplicateHalo();
    repairClicks();

    const observer = new MutationObserver(() => {
      removeDuplicateHalo();
      repairClicks();
    });

    observer.observe(document.body, {
      subtree: true,
      childList: true,
    });

    window.NoorBrainMobileDuplicateHaloClickFix = {
      version: VERSION,
      repairClicks,
      removeDuplicateHalo,
      triggerHalo,
    };

    console.info(
      `NoorBrain Mobile Duplicate HALO Click Fix ${VERSION} active`
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
})();
