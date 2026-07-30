(() => {
  "use strict";

  if (window.NoorBrainSprint3SmartHome) return;

  const API = "/api/smart-home-v3";
  const state = {
    home: {
      rooms: [],
      devices: [],
      scenes: [],
      favorites: [],
    },
    activeRoom: "",
  };

  const $ = id => document.getElementById(id);

  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: {"Content-Type": "application/json"},
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
      light: "💡",
      fan: "🌀",
      tv: "📺",
      ac: "❄️",
      plug: "🔌",
      speaker: "🔊",
      camera: "📷",
      switch: "⏻",
    }[type] || "⌁";
  }

  function mount() {
    const modules =
      document.querySelector(".nbv2-module-section")
      || document.querySelector("#nbv2Modules")
      || document.querySelector("main");

    if (!modules || $("nbs3SmartHome")) return;

    const panel = document.createElement("section");
    panel.id = "nbs3SmartHome";
    panel.className = "nbs3-panel";

    panel.innerHTML = `
      <article class="nbs3-card">
        <div class="nbs3-head">
          <div>
            <small>SPRINT 3</small>
            <h2>Smart Home</h2>
          </div>
          <div class="nbs3-actions">
            <button class="nbs3-button" id="nbs3Refresh">↻</button>
            <button class="nbs3-button primary" id="nbs3AddDevice">＋ Device</button>
          </div>
        </div>

        <div class="nbs3-room-grid" id="nbs3Rooms"></div>
        <p class="nbs3-status" id="nbs3Status">Loading home…</p>
      </article>

      <article class="nbs3-card">
        <div class="nbs3-head">
          <div>
            <small>ONE TAP</small>
            <h2>Devices</h2>
          </div>
          <div class="nbs3-actions">
            <button class="nbs3-button" id="nbs3AllOff">All Off</button>
          </div>
        </div>
        <div class="nbs3-device-grid" id="nbs3Devices"></div>
      </article>

      <article class="nbs3-card">
        <div class="nbs3-head">
          <div>
            <small>ROUTINES</small>
            <h2>Scenes</h2>
          </div>
          <div class="nbs3-actions">
            <button class="nbs3-button primary" id="nbs3AddScene">＋ Scene</button>
          </div>
        </div>
        <div class="nbs3-scene-grid" id="nbs3Scenes"></div>
      </article>
    `;

    modules.insertAdjacentElement("afterend", panel);

    if (!$("nbs3Modal")) {
      const modal = document.createElement("div");
      modal.id = "nbs3Modal";
      modal.className = "nbs3-modal";
      modal.hidden = true;
      document.body.appendChild(modal);
    }

    $("nbs3Refresh").onclick = load;
    $("nbs3AddDevice").onclick = addDeviceModal;
    $("nbs3AddScene").onclick = addSceneModal;
    $("nbs3AllOff").onclick = allOff;

    load();
  }

  async function load() {
    try {
      const payload = await request(`${API}/state`);
      state.home = payload.home;
      render();
      $("nbs3Status").textContent =
        `${state.home.rooms.length} rooms · ${state.home.devices.length} devices · ${state.home.scenes.length} scenes`;
    } catch (error) {
      $("nbs3Status").textContent = error.message;
    }
  }

  function render() {
    renderRooms();
    renderDevices();
    renderScenes();
  }

  function roomName(roomId) {
    return state.home.rooms.find(room => room.id === roomId)?.name || "Home";
  }

  function renderRooms() {
    const host = $("nbs3Rooms");

    host.innerHTML = `
      <button class="nbs3-room ${state.activeRoom === "" ? "active" : ""}" data-room="">
        <span>🏠</span><b>All Rooms</b>
        <small>${state.home.devices.length} devices</small>
      </button>
      ${state.home.rooms.map(room => {
        const count = state.home.devices.filter(device => device.room_id === room.id).length;
        return `
          <button class="nbs3-room" data-room="${safe(room.id)}">
            <span>${safe(room.icon || "🏠")}</span>
            <b>${safe(room.name)}</b>
            <small>${count} devices</small>
          </button>
        `;
      }).join("")}
    `;

    host.querySelectorAll("[data-room]").forEach(button => {
      button.onclick = () => {
        state.activeRoom = button.dataset.room;
        renderDevices();
        renderRooms();
      };
    });
  }

  function renderDevices() {
    const host = $("nbs3Devices");
    const favorites = new Set(state.home.favorites || []);

    let devices = state.home.devices;

    if (state.activeRoom) {
      devices = devices.filter(device => device.room_id === state.activeRoom);
    }

    devices = [...devices].sort(
      (a, b) => Number(favorites.has(b.id)) - Number(favorites.has(a.id))
    );

    if (!devices.length) {
      host.innerHTML = `
        <button class="nbs3-empty" id="nbs3EmptyDevice">
          ＋ Add a device
        </button>
      `;
      $("nbs3EmptyDevice").onclick = addDeviceModal;
      return;
    }

    host.innerHTML = devices.map(device => `
      <button
        class="nbs3-device ${device.state === "on" ? "on" : ""}"
        data-device="${safe(device.id)}"
      >
        <span>${icon(device.type)}</span>
        <b>${safe(device.name)}</b>
        <small class="${device.online === false ? "nbs3-device-offline" : ""}">
          ${safe(roomName(device.room_id))} · ${device.online === false ? "Offline" : "Online"}
        </small>
        <span class="nbs3-device-state">${device.state === "on" ? "ON" : "OFF"}</span>
        <button
          class="nbs3-device-favorite"
          data-favorite="${safe(device.id)}"
          title="Favorite"
        >${favorites.has(device.id) ? "★" : "☆"}</button>
      </button>
    `).join("");

    host.querySelectorAll("[data-device]").forEach(button => {
      button.onclick = event => {
        if (event.target.closest("[data-favorite]")) return;
        toggleDevice(button.dataset.device);
      };
    });

    host.querySelectorAll("[data-favorite]").forEach(button => {
      button.onclick = event => {
        event.preventDefault();
        event.stopPropagation();
        toggleFavorite(button.dataset.favorite);
      };
    });
  }

  function renderScenes() {
    const host = $("nbs3Scenes");

    if (!state.home.scenes.length) {
      host.innerHTML = `
        <button class="nbs3-empty" id="nbs3EmptyScene">
          ＋ Create a scene
        </button>
      `;
      $("nbs3EmptyScene").onclick = addSceneModal;
      return;
    }

    host.innerHTML = state.home.scenes.map(scene => `
      <button class="nbs3-scene" data-scene="${safe(scene.id)}">
        <span>${safe(scene.icon || "⚡")}</span>
        <b>${safe(scene.name)}</b>
        <small>${scene.actions?.length || 0} actions</small>
      </button>
    `).join("");

    host.querySelectorAll("[data-scene]").forEach(button => {
      button.onclick = () => runScene(button.dataset.scene);
    });
  }

  async function toggleDevice(deviceId) {
    $("nbs3Status").textContent = "Updating device…";

    try {
      await request(`${API}/devices/${deviceId}/toggle`, {
        method: "POST",
        body: "{}",
      });
      await load();
    } catch (error) {
      $("nbs3Status").textContent = error.message;
    }
  }

  async function toggleFavorite(deviceId) {
    try {
      await request(`${API}/favorites/${deviceId}`, {
        method: "POST",
        body: "{}",
      });
      await load();
    } catch (error) {
      $("nbs3Status").textContent = error.message;
    }
  }

  async function allOff() {
    const active = state.home.devices.filter(device => device.state === "on");

    $("nbs3Status").textContent = `Turning off ${active.length} devices…`;

    await Promise.allSettled(
      active.map(device =>
        request(`${API}/devices/${device.id}/state`, {
          method: "POST",
          body: JSON.stringify({state: "off"}),
        })
      )
    );

    await load();
  }

  async function runScene(sceneId) {
    $("nbs3Status").textContent = "Running scene…";

    try {
      const result = await request(`${API}/scenes/${sceneId}/run`, {
        method: "POST",
        body: "{}",
      });

      const failed = result.results.filter(item => item.status !== "ok").length;
      $("nbs3Status").textContent =
        failed ? `Scene completed with ${failed} errors.` : "Scene completed.";
      await load();
    } catch (error) {
      $("nbs3Status").textContent = error.message;
    }
  }

  function modal(html) {
    const host = $("nbs3Modal");
    host.hidden = false;
    host.innerHTML = html;

    host.querySelector("[data-close]")?.addEventListener("click", () => {
      host.hidden = true;
    });
  }

  function roomOptions() {
    return state.home.rooms.map(room => `
      <option value="${safe(room.id)}">${safe(room.name)}</option>
    `).join("");
  }

  function addDeviceModal() {
    modal(`
      <form class="nbs3-modal-card" id="nbs3DeviceForm">
        <h2>Add Device</h2>

        <label>
          Device name
          <input name="name" required placeholder="Hall Light">
        </label>

        <label>
          Type
          <select name="type">
            <option value="light">Light</option>
            <option value="fan">Fan</option>
            <option value="plug">Plug</option>
            <option value="tv">TV</option>
            <option value="ac">AC</option>
            <option value="speaker">Speaker</option>
            <option value="switch">Switch</option>
          </select>
        </label>

        <label>
          Room
          <select name="room_id">${roomOptions()}</select>
        </label>

        <label>
          ON webhook (optional)
          <input name="webhook_on" placeholder="http://device/on">
        </label>

        <label>
          OFF webhook (optional)
          <input name="webhook_off" placeholder="http://device/off">
        </label>

        <div class="nbs3-modal-actions">
          <button type="button" class="nbs3-button" data-close>Cancel</button>
          <button class="nbs3-button primary" type="submit">Save Device</button>
        </div>
      </form>
    `);

    $("nbs3DeviceForm").onsubmit = async event => {
      event.preventDefault();

      try {
        await request(`${API}/devices`, {
          method: "POST",
          body: JSON.stringify(
            Object.fromEntries(new FormData(event.target).entries())
          ),
        });

        $("nbs3Modal").hidden = true;
        await load();
      } catch (error) {
        $("nbs3Status").textContent = error.message;
      }
    };
  }

  function addSceneModal() {
    const deviceChecks = state.home.devices.map(device => `
      <label>
        ${safe(device.name)}
        <select name="device:${safe(device.id)}">
          <option value="">No change</option>
          <option value="on">ON</option>
          <option value="off">OFF</option>
        </select>
      </label>
    `).join("");

    modal(`
      <form class="nbs3-modal-card" id="nbs3SceneForm">
        <h2>Create Scene</h2>

        <label>
          Scene name
          <input name="name" required placeholder="Good Night">
        </label>

        <label>
          Icon
          <input name="icon" value="⚡">
        </label>

        ${deviceChecks || "<p>Add devices before creating a scene.</p>"}

        <div class="nbs3-modal-actions">
          <button type="button" class="nbs3-button" data-close>Cancel</button>
          <button class="nbs3-button primary" type="submit">Save Scene</button>
        </div>
      </form>
    `);

    $("nbs3SceneForm").onsubmit = async event => {
      event.preventDefault();

      const form = new FormData(event.target);
      const actions = [];

      for (const device of state.home.devices) {
        const selected = form.get(`device:${device.id}`);
        if (selected) {
          actions.push({
            device_id: device.id,
            state: selected,
          });
        }
      }

      try {
        await request(`${API}/scenes`, {
          method: "POST",
          body: JSON.stringify({
            name: form.get("name"),
            icon: form.get("icon"),
            actions,
          }),
        });

        $("nbs3Modal").hidden = true;
        await load();
      } catch (error) {
        $("nbs3Status").textContent = error.message;
      }
    };
  }

  window.NoorBrainSprint3SmartHome = {
    version: "3.0.0",
    load,
    toggleDevice,
    runScene,
    allOff,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
