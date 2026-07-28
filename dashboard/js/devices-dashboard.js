(() => {
  "use strict";

  const API_BASE = "/api/devices";
  const REFRESH_MS = 10000;

  const state = {
    devices: [],
    timer: null,
    mounted: false,
  };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  async function api(path = "") {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    const raw = await response.text();
    let body;
    try {
      body = JSON.parse(raw);
    } catch {
      body = { detail: raw };
    }

    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return body;
  }

  function stateLabel(device) {
    const value = String(device.state || "unknown").toLowerCase();
    if (value === "on") return "ON";
    if (value === "off") return "OFF";
    return "UNKNOWN";
  }

  function iconForType(type) {
    const icons = {
      light: "💡",
      fan: "🌀",
      plug: "🔌",
      relay: "⚡",
      switch: "🎚️",
      sensor: "📡",
      motion_sensor: "🚶",
      door_sensor: "🚪",
      temperature_sensor: "🌡️",
      humidity_sensor: "💧",
      camera: "📷",
      other: "🔧",
    };
    return icons[type] || icons.other;
  }

  function renderCard(device) {
    const card = el("article", "nb-device-card");
    card.dataset.deviceId = device.id;

    const header = el("div", "nb-device-card__header");
    const icon = el("div", "nb-device-card__icon", iconForType(device.device_type));
    const titleWrap = el("div", "nb-device-card__title-wrap");
    const title = el("h3", "nb-device-card__title", device.name || "Unnamed device");
    const subtitle = el(
      "div",
      "nb-device-card__subtitle",
      `${device.room || "Unassigned"} · ${device.device_type || "other"}`
    );

    titleWrap.append(title, subtitle);

    const badge = el(
      "span",
      `nb-device-badge ${device.online ? "is-online" : "is-offline"}`,
      device.online ? "ONLINE" : "OFFLINE"
    );

    header.append(icon, titleWrap, badge);

    const body = el("div", "nb-device-card__body");

    const rows = [
      ["State", stateLabel(device)],
      ["IP", device.ip_address || "—"],
      ["Manufacturer", device.manufacturer || "—"],
      ["Model", device.model || "—"],
    ];

    for (const [label, value] of rows) {
      const row = el("div", "nb-device-row");
      row.append(
        el("span", "nb-device-row__label", label),
        el("span", "nb-device-row__value", value)
      );
      body.append(row);
    }

    card.append(header, body);
    return card;
  }

  function renderSummary(devices) {
    const summary = document.querySelector("#nbDevicesSummary");
    if (!summary) return;

    const online = devices.filter((item) => item.online).length;
    const on = devices.filter((item) => String(item.state).toLowerCase() === "on").length;

    summary.innerHTML = "";
    const metrics = [
      ["Total", devices.length],
      ["Online", online],
      ["Offline", devices.length - online],
      ["Powered On", on],
    ];

    for (const [label, value] of metrics) {
      const metric = el("div", "nb-device-metric");
      metric.append(
        el("div", "nb-device-metric__value", String(value)),
        el("div", "nb-device-metric__label", label)
      );
      summary.append(metric);
    }
  }

  function renderDevices(devices) {
    const grid = document.querySelector("#nbDevicesGrid");
    const empty = document.querySelector("#nbDevicesEmpty");
    const error = document.querySelector("#nbDevicesError");

    if (!grid || !empty || !error) return;

    error.hidden = true;
    grid.innerHTML = "";

    if (!devices.length) {
      empty.hidden = false;
      return;
    }

    empty.hidden = true;

    for (const device of devices) {
      grid.append(renderCard(device));
    }
  }

  function setLoading(loading) {
    const status = document.querySelector("#nbDevicesStatus");
    if (!status) return;
    status.textContent = loading ? "Loading devices…" : "Live";
    status.classList.toggle("is-loading", loading);
  }

  function showError(message) {
    const error = document.querySelector("#nbDevicesError");
    const status = document.querySelector("#nbDevicesStatus");

    if (error) {
      error.hidden = false;
      error.textContent = `Devices unavailable: ${message}`;
    }

    if (status) {
      status.textContent = "Error";
      status.classList.remove("is-loading");
    }
  }

  async function loadDevices() {
    setLoading(true);

    try {
      const body = await api("");
      state.devices = Array.isArray(body.devices) ? body.devices : [];
      renderSummary(state.devices);
      renderDevices(state.devices);

      const status = document.querySelector("#nbDevicesStatus");
      if (status) {
        status.textContent = "Live";
        status.classList.remove("is-loading");
      }
    } catch (error) {
      showError(error.message || String(error));
    }
  }

  function ensureSection() {
    if (document.querySelector("#nbDevicesSection")) {
      return document.querySelector("#nbDevicesSection");
    }

    const section = el("section", "nb-devices-section");
    section.id = "nbDevicesSection";

    const top = el("div", "nb-devices-top");
    const headingWrap = el("div");
    headingWrap.append(
      el("h2", "nb-devices-title", "Devices"),
      el("p", "nb-devices-subtitle", "Registered smart-home devices and live status")
    );

    const status = el("span", "nb-devices-status", "Loading devices…");
    status.id = "nbDevicesStatus";
    top.append(headingWrap, status);

    const summary = el("div", "nb-devices-summary");
    summary.id = "nbDevicesSummary";

    const error = el("div", "nb-devices-error");
    error.id = "nbDevicesError";
    error.hidden = true;

    const empty = el("div", "nb-devices-empty");
    empty.id = "nbDevicesEmpty";
    empty.hidden = true;
    empty.innerHTML = `
      <div class="nb-devices-empty__icon">🔌</div>
      <h3>No devices registered yet</h3>
      <p>Devices added through the NoorBrain API will appear here automatically.</p>
    `;

    const grid = el("div", "nb-devices-grid");
    grid.id = "nbDevicesGrid";

    section.append(top, summary, error, empty, grid);

    const preferred =
      document.querySelector("main") ||
      document.querySelector("#app") ||
      document.querySelector(".dashboard-content") ||
      document.body;

    preferred.append(section);
    return section;
  }

  function addNavigationLink() {
    if (document.querySelector('[data-noor-devices-nav="true"]')) return;

    const menu =
      document.querySelector("nav") ||
      document.querySelector(".sidebar") ||
      document.querySelector(".navigation");

    if (!menu) return;

    const link = document.createElement("a");
    link.href = "#nbDevicesSection";
    link.textContent = "Devices";
    link.dataset.noorDevicesNav = "true";
    link.className = "nb-devices-nav-link";

    menu.append(link);
  }

  function mount() {
    if (state.mounted) return;
    state.mounted = true;

    ensureSection();
    addNavigationLink();
    loadDevices();

    state.timer = window.setInterval(loadDevices, REFRESH_MS);
    window.addEventListener("beforeunload", () => {
      if (state.timer) window.clearInterval(state.timer);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

  window.NoorDevicesDashboard = {
    refresh: loadDevices,
    get devices() {
      return [...state.devices];
    },
  };
})();
