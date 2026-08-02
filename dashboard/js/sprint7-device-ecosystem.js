(() => {
  "use strict";

  if (window.NoorBrainSprint7Devices) return;

  const API = "/api/device-ecosystem-v7";

  const state = {
    ecosystem: {
      candidates: [],
      paired: [],
      settings: {},
    },
    smartHome: {
      rooms: [],
    },
  };

  const $ = id => document.getElementById(id);

  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      cache: "no-store",
      ...options,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return data;
  }

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function icon(type) {
    return {
      noorbrain: "🧠",
      light: "💡",
      fan: "🌀",
      plug: "🔌",
      tv: "📺",
      ac: "❄️",
      speaker: "🔊",
      camera: "📷",
      switch: "⏻",
      sensor: "◉",
      unknown: "⌁",
    }[type] || "⌁";
  }

  function mount() {
    const devices =
      document.querySelector(".nbv2-device-section")
      || document.querySelector("#nbv2Devices")
      || document.querySelector("main");

    if (!devices || $("nbs7DeviceEcosystem")) return;

    const panel = document.createElement("section");
    panel.id = "nbs7DeviceEcosystem";
    panel.className = "nbs7-panel";

    panel.innerHTML = `
      <article class="nbs7-card">
        <div class="nbs7-head">
          <div>
            <small>SPRINT 7</small>
            <h2>Device Ecosystem</h2>
          </div>
          <div class="nbs7-actions">
            <button class="nbs7-button" id="nbs7Refresh">↻</button>
            <button class="nbs7-button primary" id="nbs7Discover">Discover</button>
            <button class="nbs7-button" id="nbs7Manual">＋ Manual</button>
          </div>
        </div>

        <div class="nbs7-hero">
          <div>
            <small>ONE-CLICK ONBOARDING</small>
            <h3>Add home devices without terminal commands</h3>
            <span>Discover, test, pair and assign a room.</span>
          </div>
          <div class="nbs7-badge" id="nbs7Badge">READY</div>
        </div>

        <div class="nbs7-grid" id="nbs7Candidates"></div>
        <p class="nbs7-status" id="nbs7Status">Loading device ecosystem…</p>
      </article>

      <article class="nbs7-card">
        <div class="nbs7-head">
          <div>
            <small>PAIRED</small>
            <h2>Home Devices</h2>
          </div>
          <div class="nbs7-actions">
            <button class="nbs7-button" id="nbs7HealthAll">Health Check</button>
          </div>
        </div>

        <div class="nbs7-grid" id="nbs7Paired"></div>
      </article>

      <article class="nbs7-card">
        <div class="nbs7-head">
          <div>
            <small>SETTINGS</small>
            <h2>Discovery & Health</h2>
          </div>
          <div class="nbs7-actions">
            <button class="nbs7-button primary" id="nbs7SaveSettings">Save</button>
          </div>
        </div>

        <div class="nbs7-settings">
          <label>
            Auto discovery
            <select id="nbs7AutoDiscovery">
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </label>

          <label>
            Health interval
            <select id="nbs7HealthInterval">
              <option value="15">15 seconds</option>
              <option value="30">30 seconds</option>
              <option value="60">1 minute</option>
              <option value="300">5 minutes</option>
            </select>
          </label>

          <label>
            Default room
            <select id="nbs7DefaultRoom"></select>
          </label>
        </div>
      </article>
    `;

    devices.insertAdjacentElement("afterend", panel);

    if (!$("nbs7Modal")) {
      const modal = document.createElement("div");
      modal.id = "nbs7Modal";
      modal.className = "nbs7-modal";
      modal.hidden = true;
      document.body.appendChild(modal);
    }

    bind();
    load();
  }

  function bind() {
    $("nbs7Refresh").onclick = load;
    $("nbs7Discover").onclick = discover;
    $("nbs7Manual").onclick = manualModal;
    $("nbs7HealthAll").onclick = healthAll;
    $("nbs7SaveSettings").onclick = saveSettings;
  }

  async function load() {
    try {
      const [ecosystem, smart] = await Promise.all([
        request(`${API}/state`),
        request("/api/smart-home-v3/state").catch(() => ({
          home: {rooms: []},
        })),
      ]);

      state.ecosystem = ecosystem.ecosystem;
      state.smartHome = smart.home || {rooms: []};

      renderCandidates();
      renderPaired();
      renderSettings();

      $("nbs7Status").textContent =
        `${state.ecosystem.candidates.length} discovered · ${state.ecosystem.paired.length} paired`;

      $("nbs7Badge").textContent = "READY";
    } catch (error) {
      $("nbs7Status").textContent = error.message;
      $("nbs7Badge").textContent = "ERROR";
    }
  }

  async function discover() {
    $("nbs7Status").textContent = "Discovering known LAN devices…";
    $("nbs7Badge").textContent = "SCANNING";

    try {
      const data = await request(`${API}/discover`, {
        method: "POST",
        body: "{}",
      });

      $("nbs7Status").textContent =
        `Discovery completed. ${data.found} network entries found.`;

      await load();
    } catch (error) {
      $("nbs7Status").textContent = error.message;
      $("nbs7Badge").textContent = "ERROR";
    }
  }

  function renderCandidates() {
    const host = $("nbs7Candidates");

    if (!state.ecosystem.candidates.length) {
      host.innerHTML = `
        <button class="nbs7-empty" id="nbs7EmptyCandidate">
          Tap Discover or add a device manually.
        </button>
      `;

      $("nbs7EmptyCandidate").onclick = manualModal;
      return;
    }

    host.innerHTML = state.ecosystem.candidates.map(candidate => {
      const probe = candidate.probe || {};

      return `
        <article class="nbs7-candidate">
          <span>${icon(candidate.type)}</span>
          <b>${safe(candidate.name)}</b>
          <small>${safe(candidate.base_url || candidate.host || "")}</small>
          <small>
            ${probe.online === true
              ? `Online · ${safe(probe.latency_ms)} ms`
              : probe.online === false
                ? "Probe failed"
                : safe(candidate.source || "discovered")}
          </small>
          <div class="nbs7-card-actions">
            <button
              class="nbs7-button"
              data-probe="${safe(candidate.id)}"
            >Test</button>
            <button
              class="nbs7-button primary"
              data-pair="${safe(candidate.id)}"
            >Pair</button>
          </div>
        </article>
      `;
    }).join("");

    host.querySelectorAll("[data-probe]").forEach(button => {
      button.onclick = () => probeCandidate(button.dataset.probe);
    });

    host.querySelectorAll("[data-pair]").forEach(button => {
      button.onclick = () => pairModal(button.dataset.pair);
    });
  }

  function renderPaired() {
    const host = $("nbs7Paired");

    if (!state.ecosystem.paired.length) {
      host.innerHTML = `
        <div class="nbs7-empty">
          No devices paired yet.
        </div>
      `;
      return;
    }

    host.innerHTML = state.ecosystem.paired.map(device => `
      <article class="nbs7-device ${device.online ? "online" : "offline"}">
        <span>${icon(device.type)}</span>
        <b>${safe(device.name)}</b>
        <small>${safe(roomName(device.room_id))}</small>
        <small>${safe(device.base_url)}</small>
        <div class="nbs7-state ${device.online ? "online" : "offline"}">
          ${device.online ? "ONLINE" : "OFFLINE"}
        </div>
        <div class="nbs7-card-actions">
          <button
            class="nbs7-button"
            data-health="${safe(device.id)}"
          >Health</button>
          <button
            class="nbs7-button danger"
            data-unpair="${safe(device.id)}"
          >Remove</button>
        </div>
      </article>
    `).join("");

    host.querySelectorAll("[data-health]").forEach(button => {
      button.onclick = () => healthDevice(button.dataset.health);
    });

    host.querySelectorAll("[data-unpair]").forEach(button => {
      button.onclick = () => unpair(button.dataset.unpair);
    });
  }

  function roomName(roomId) {
    return state.smartHome.rooms.find(room => room.id === roomId)?.name
      || roomId
      || "Home";
  }

  function roomOptions(selected = "") {
    const rooms = state.smartHome.rooms.length
      ? state.smartHome.rooms
      : [{id: "hall", name: "Hall"}];

    return rooms.map(room => `
      <option
        value="${safe(room.id)}"
        ${room.id === selected ? "selected" : ""}
      >${safe(room.name)}</option>
    `).join("");
  }

  function renderSettings() {
    const settings = state.ecosystem.settings || {};

    $("nbs7AutoDiscovery").value =
      String(settings.auto_discovery !== false);

    $("nbs7HealthInterval").value =
      String(settings.health_interval_seconds || 30);

    $("nbs7DefaultRoom").innerHTML =
      roomOptions(settings.default_room || "hall");
  }

  async function probeCandidate(candidateId) {
    $("nbs7Status").textContent = "Testing device connection…";

    try {
      const data = await request(
        `${API}/candidates/${candidateId}/probe`,
        {
          method: "POST",
          body: "{}",
        }
      );

      $("nbs7Status").textContent = data.candidate.probe.online
        ? `Device online · ${data.candidate.probe.latency_ms} ms`
        : `Device unavailable: ${data.candidate.probe.error}`;

      await load();
    } catch (error) {
      $("nbs7Status").textContent = error.message;
    }
  }

  async function healthDevice(deviceId) {
    $("nbs7Status").textContent = "Checking device health…";

    try {
      const data = await request(
        `${API}/paired/${deviceId}/health`,
        {
          method: "POST",
          body: "{}",
        }
      );

      $("nbs7Status").textContent = data.device.online
        ? `Device online · ${data.device.last_health.latency_ms} ms`
        : `Device offline: ${data.device.last_health.error}`;

      await load();
    } catch (error) {
      $("nbs7Status").textContent = error.message;
    }
  }

  async function healthAll() {
    $("nbs7Status").textContent = "Checking all devices…";

    try {
      const data = await request(`${API}/paired/health-all`, {
        method: "POST",
        body: "{}",
      });

      const online = data.results.filter(item => item.online).length;

      $("nbs7Status").textContent =
        `${online}/${data.results.length} devices online.`;

      await load();
    } catch (error) {
      $("nbs7Status").textContent = error.message;
    }
  }

  async function unpair(deviceId) {
    if (!confirm("Remove this device from NoorBrain?")) return;

    try {
      await request(`${API}/paired/${deviceId}`, {
        method: "DELETE",
      });

      $("nbs7Status").textContent = "Device removed.";
      await load();
    } catch (error) {
      $("nbs7Status").textContent = error.message;
    }
  }

  async function saveSettings() {
    try {
      await request(`${API}/settings`, {
        method: "POST",
        body: JSON.stringify({
          auto_discovery: $("nbs7AutoDiscovery").value === "true",
          health_interval_seconds: Number(
            $("nbs7HealthInterval").value
          ),
          default_room: $("nbs7DefaultRoom").value,
        }),
      });

      $("nbs7Status").textContent = "Device ecosystem settings saved.";
      await load();
    } catch (error) {
      $("nbs7Status").textContent = error.message;
    }
  }

  function modal(html) {
    const host = $("nbs7Modal");
    host.hidden = false;
    host.innerHTML = html;

    host.querySelector("[data-close]")?.addEventListener("click", () => {
      host.hidden = true;
    });
  }

  function manualModal() {
    modal(`
      <form class="nbs7-modal-card" id="nbs7ManualForm">
        <h2>Add Device Address</h2>

        <label>
          Device name
          <input name="name" required placeholder="Hall ESP32">
        </label>

        <label>
          Device type
          <select name="type">
            <option value="switch">Switch</option>
            <option value="light">Light</option>
            <option value="fan">Fan</option>
            <option value="plug">Plug</option>
            <option value="camera">Camera</option>
            <option value="speaker">Speaker</option>
            <option value="sensor">Sensor</option>
          </select>
        </label>

        <label>
          Device URL or IP
          <input
            name="base_url"
            required
            placeholder="http://192.168.2.50"
          >
        </label>

        <div class="nbs7-modal-actions">
          <button type="button" class="nbs7-button" data-close>Cancel</button>
          <button class="nbs7-button primary" type="submit">Add</button>
        </div>
      </form>
    `);

    $("nbs7ManualForm").onsubmit = async event => {
      event.preventDefault();

      try {
        const data = await request(`${API}/candidates`, {
          method: "POST",
          body: JSON.stringify(
            Object.fromEntries(new FormData(event.target).entries())
          ),
        });

        $("nbs7Modal").hidden = true;
        await load();
        pairModal(data.candidate.id);
      } catch (error) {
        $("nbs7Status").textContent = error.message;
      }
    };
  }

  function pairModal(candidateId) {
    const candidate = state.ecosystem.candidates.find(
      item => item.id === candidateId
    );

    if (!candidate) return;

    modal(`
      <form class="nbs7-modal-card" id="nbs7PairForm">
        <h2>Pair Device</h2>

        <input type="hidden" name="candidate_id" value="${safe(candidate.id)}">

        <label>
          Device name
          <input name="name" required value="${safe(candidate.name)}">
        </label>

        <label>
          Type
          <select name="type">
            ${["switch","light","fan","plug","camera","speaker","sensor","tv","ac"]
              .map(type => `
                <option
                  value="${type}"
                  ${type === candidate.type ? "selected" : ""}
                >${type}</option>
              `).join("")}
          </select>
        </label>

        <label>
          Room
          <select name="room_id">
            ${roomOptions(
              state.ecosystem.settings?.default_room || "hall"
            )}
          </select>
        </label>

        <label>
          Base URL
          <input name="base_url" value="${safe(candidate.base_url)}">
        </label>

        <label>
          Health path
          <input name="health_path" value="/">
        </label>

        <label>
          ON command path
          <input name="command_on_path" placeholder="/on">
        </label>

        <label>
          OFF command path
          <input name="command_off_path" placeholder="/off">
        </label>

        <div class="nbs7-modal-actions">
          <button type="button" class="nbs7-button" data-close>Cancel</button>
          <button class="nbs7-button primary" type="submit">Pair Device</button>
        </div>
      </form>
    `);

    $("nbs7PairForm").onsubmit = async event => {
      event.preventDefault();

      try {
        await request(`${API}/pair`, {
          method: "POST",
          body: JSON.stringify(
            Object.fromEntries(new FormData(event.target).entries())
          ),
        });

        $("nbs7Modal").hidden = true;
        $("nbs7Status").textContent =
          "Device paired and added to Smart Home.";

        await load();

        window.NoorBrainSprint3SmartHome?.load?.();
      } catch (error) {
        $("nbs7Status").textContent = error.message;
      }
    };
  }

  window.NoorBrainSprint7Devices = {
    version: "7.0.0",
    load,
    discover,
    healthAll,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
