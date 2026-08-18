(() => {
"use strict";

if (window.NoorAutomationCenterRouterV12) return;

function open(tab="smart") {
  if (!window.NoorAutomationCenterV12?.open) {
    console.error("AUTOMATION CENTER NOT READY");
    return false;
  }

  window.NoorAutomationCenterV12.open(tab);
  return true;
}

document.addEventListener("click", event => {
  const el = event.target.closest?.(
    "[data-module],[data-feature],[data-action]"
  );

  if (!el) return;

  const value = String(
    el.dataset.module ||
    el.dataset.feature ||
    ""
  ).toLowerCase();

  const map = {
    automation: "smart",
    "smart-automation": "smart",
    "smart-rules": "smart",

    scenes: "scenes",
    scene: "scenes",

    groups: "groups",
    "device-groups": "groups",

    routines: "routines",
    routine: "routines",

    rules: "reminders",
    reminders: "reminders",
    "reminder-rules": "reminders"
  };

  const tab = map[value];

  if (!tab) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();

  open(tab);
}, true);

window.NoorAutomationCenterRouterV12 = Object.freeze({
  version: "12.3.0",
  open
});

console.log(
  "NOOR_AUTOMATION_CENTER_ROUTER_V12_READY"
);
})();
