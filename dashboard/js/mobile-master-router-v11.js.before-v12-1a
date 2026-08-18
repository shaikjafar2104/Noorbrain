(() => {
  "use strict";

  if (window.__NOOR_MOBILE_MASTER_ROUTER_V11__) return;
  window.__NOOR_MOBILE_MASTER_ROUTER_V11__ = true;

  const featureMap = {
    devices: "home",
    automation: "ai",
    habits: "ai",
    insights: "ai",
    prayer: "islamic",
    reminders: "islamic",
    family: "family",
    voice: "voice"
  };

  const studioMap = {
    zones: "/studio#vision-zones",
    presence: "/studio#person-presence",
    faces: "/studio#face-identity",
    rules: "/studio#reminder-rules",
    notifications: "/studio#notifications",
    media: "/studio#media-library"
  };

  function openSettings() {
    if (window.NoorMobileSettingsV11?.open) {
      window.NoorMobileSettingsV11.open();
      return true;
    }

    console.error("NOOR SETTINGS NOT READY");
    return false;
  }

  function openUnified(feature) {
    if (window.NoorBrainUnifiedUI?.open) {
      return window.NoorBrainUnifiedUI.open(feature);
    }

    return false;
  }

  document.addEventListener("click", event => {
    const button =
      event.target.closest?.("[data-module]");

    if (!button) return;

    const module = button.dataset.module;

    if (module === "settings") {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      openSettings();
      return;
    }

    if (module === "rules") {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      if (window.NoorMobileRulesV12?.open) {
        window.NoorMobileRulesV12.open();
      } else {
        console.error(
          "NOOR RULES V12 NOT READY"
        );
      }

      return;
    }

    if (module === "vision") {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const camera =
        document.getElementById(
          "nbv2CameraSection"
        );

      if (camera) {
        camera.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      } else {
        location.href = "/studio#vision";
      }

      return;
    }

    const feature = featureMap[module];

    if (feature) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      if (!openUnified(feature)) {
        console.warn(
          "NOOR FEATURE UNAVAILABLE:",
          feature
        );
      }

      return;
    }

    const target = studioMap[module];

    if (target) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      location.href = target;
    }
  }, true);

  console.log(
    "NOOR_MOBILE_MASTER_ROUTER_V11_READY"
  );
})();
