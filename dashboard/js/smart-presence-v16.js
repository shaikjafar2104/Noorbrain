(() => {
  "use strict";
  if (window.NoorBrainSmartPresenceV16) return;

  const state = { unlocked: false, initialized: false, lastReminder: null };
  const audio = new Audio();
  audio.preload = "auto";

  async function json(path, options = {}) {
    const response = await fetch(path, { cache: "no-store", ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function mount() {
    if (document.getElementById("nbSmartPresenceV16")) return;
    const host = document.querySelector("main") || document.body;
    const panel = document.createElement("section");
    panel.id = "nbSmartPresenceV16";
    panel.className = "nb-sp-card";
    panel.innerHTML = `
      <div class="nb-sp-head">
        <div><small>NOORBRAIN AI CONTROL</small><h2>Smart Presence & Audio</h2></div>
        <span class="nb-sp-live">Protected</span>
      </div>
      <div class="nb-sp-grid">
        <div><b>Vision AI</b><span>Detects a person; movement alone does not replay reminders.</span></div>
        <div><b>Face AI</b><span>Recognizes saved people and stores unknown snapshots for review.</span></div>
        <div><b>Habit AI</b><span>Learns routines and proposes suggestions; you approve automations.</span></div>
        <div><b>HALO</b><span>Voice commands and quick replies through app or Raspberry Pi.</span></div>
      </div>
      <div class="nb-sp-actions">
        <button id="nbEnableAppAudio">Enable App Audio</button>
        <button id="nbTestPiMic">Test Pi Mic + Speaker</button>
        <button id="nbReviewFaces">Review Face Gallery</button>
        <span id="nbSpStatus">Same-room reminder protection active.</span>
      </div>
      <div id="nbFaceGallery" class="nb-sp-gallery" hidden></div>`;
    host.appendChild(panel);
    panel.querySelector("#nbEnableAppAudio").addEventListener("click", unlockAudio);
    panel.querySelector("#nbTestPiMic").addEventListener("click", testPiMic);
    panel.querySelector("#nbReviewFaces").addEventListener("click", loadGallery);
  }

  async function unlockAudio() {
    // Start an Audio element inside the user gesture. Android/iPhone browsers
    // then permit later recorded reminder playback without a Send button.
    audio.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";
    try { await audio.play(); audio.pause(); } catch (_) {}
    state.unlocked = true;
    const button = document.getElementById("nbEnableAppAudio");
    if (button) {
      button.textContent = "App Audio Enabled";
      button.classList.add("enabled");
    }
    document.getElementById("nbSpStatus").textContent =
      "Recorded reminders will play on this device and Raspberry Pi.";
  }

  async function testPiMic() {
    const status = document.getElementById("nbSpStatus");
    status.textContent = "Recording 3 seconds from Raspberry Pi microphone…";
    try {
      const captured = await json("/api/dual-audio-v15/pi/record", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seconds: 3 }),
      });
      const recording = captured.recording || {};
      await json("/api/dual-audio-v15/play", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio_base64: recording.audio_base64,
          format: recording.format || "wav",
        }),
      });
      if (state.unlocked && recording.audio_base64) {
        audio.src = `data:audio/wav;base64,${recording.audio_base64}`;
        await audio.play();
      }
      status.textContent = "Pi microphone captured; playback routed to Pi and app.";
    } catch (error) {
      status.textContent = `Pi audio test failed: ${error.message}`;
    }
  }

  async function loadGallery() {
    const gallery = document.getElementById("nbFaceGallery");
    gallery.hidden = false;
    gallery.textContent = "Loading…";
    try {
      const result = await json("/api/person-gallery/unknown?limit=24");
      gallery.innerHTML = result.items.length ? result.items.map(item => `
        <article data-id="${escape(item.id)}">
          <img src="${escape(item.image_url)}?v=${escape(item.timestamp)}" alt="Unknown person">
          <span>Needs review</span>
          <button class="nbFaceDelete" data-id="${escape(item.id)}">Delete</button>
        </article>`).join("") : "<p>No unknown faces saved yet.</p>";
      gallery.querySelectorAll(".nbFaceDelete").forEach(button => {
        button.addEventListener("click", async () => {
          await json(`/api/person-gallery/unknown/${encodeURIComponent(button.dataset.id)}`, { method: "DELETE" });
          loadGallery();
        });
      });
    } catch (error) {
      gallery.textContent = `Gallery unavailable: ${error.message}`;
    }
  }

  async function pollReminders() {
    try {
      const result = await json("/reminder-rules?history_limit=10");
      const newest = (result.history || [])[0];
      if (!newest) return;
      const id = newest.reminder_id;
      if (!state.initialized) {
        state.initialized = true;
        state.lastReminder = id;
        return;
      }
      if (id === state.lastReminder) return;
      state.lastReminder = id;
      if (!state.unlocked || !newest.app_audio_url) return;
      audio.src = newest.app_audio_url;
      await audio.play();
    } catch (_) {
      // Background polling must never affect the rest of the app.
    }
  }

  function start() {
    mount();
    pollReminders();
    setInterval(pollReminders, 2000);
  }

  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", start, { once: true })
    : start();

  window.NoorBrainSmartPresenceV16 = Object.freeze({
    version: "16.0.0",
    loadGallery,
    unlockAudio,
    testPiMic,
  });
})();
