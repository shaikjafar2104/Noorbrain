(() => {
  "use strict";
  if (window.NoorBrainPiWakeV16) return;
  async function load() {
    try {
      const response = await fetch("/api/pi-wake-v16/health", { cache: "no-store" });
      const data = await response.json();
      let panel = document.getElementById("nbPiWakeV16");
      if (!panel) {
        panel = document.createElement("section");
        panel.id = "nbPiWakeV16";
        panel.className = "nb-pi-wake";
        (document.querySelector("main") || document.body).appendChild(panel);
      }
      const event = data.last_event || {};
      panel.innerHTML = `<div><small>RASPBERRY PI VOICE</small><h3>Noor Hands-Free</h3><p>Say <b>“Noor”</b> or <b>“Hey Noor”</b></p></div><div class="nb-pw-state">${data.armed ? "Listening for command" : "Wake listener ready"}<span>${event.text ? `Last heard: ${String(event.text).replaceAll("<", "&lt;")}` : "No command yet"}</span></div>`;
    } catch (_) {}
  }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", load, { once: true }) : load();
  setInterval(load, 5000);
  window.NoorBrainPiWakeV16 = Object.freeze({ version: "16.1.0", load });
})();
