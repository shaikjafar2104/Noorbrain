(() => {
  "use strict";

  if (window.__NOOR_LIVE_STATUS_V12__) return;
  window.__NOOR_LIVE_STATUS_V12__ = true;

  const API = {
    health: "/health",
    home: "/api/smart-home-runtime/graph",
    vision: "/api/vision-intelligence/health",
    presence: "/api/person-presence/health",
    prayer: "/api/prayer-intelligence/health",
    rules: "/reminder-rules",
    automation: "/api/smart-automation/health",
    runtime: "/api/noor-settings-v11/runtime/status"
  };

  let timer = null;
  let busy = false;

  async function json(url) {
    const controller = new AbortController();

    const timeout = setTimeout(
      () => controller.abort(),
      5000
    );

    try {
      const r = await fetch(url, {
        cache: "no-store",
        signal: controller.signal
      });

      if (!r.ok) {
        throw new Error(`HTTP ${r.status}`);
      }

      return await r.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  function safe(result) {
    return result.status === "fulfilled"
      ? result.value
      : null;
  }

  function addStyle() {
    if (document.getElementById(
      "nbLiveStatusStyleV12"
    )) return;

    const style = document.createElement("style");
    style.id = "nbLiveStatusStyleV12";

    style.textContent = `
      .nbcn-folder {
        position: relative;
      }

      .nb-live-row {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 10px;
        min-height: 17px;
        font-size: 10px;
        opacity: .82;
      }

      .nb-live-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #8090a0;
        flex: 0 0 auto;
      }

      .nb-live-dot.ok {
        background: #5de58c;
        box-shadow:
          0 0 8px rgba(93,229,140,.55);
      }

      .nb-live-dot.warn {
        background: #f4bd50;
      }

      .nb-live-dot.bad {
        background: #ef6b6b;
      }

      .nb-live-value {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .nb-live-refresh {
        border: 0;
        border-radius: 10px;
        padding: 8px 11px;
        background: rgba(255,255,255,.07);
        color: white;
        font-size: 11px;
      }

      .nb-live-refresh[disabled] {
        opacity: .45;
      }

      .nbcn-item-live {
        display: block;
        margin-top: 4px;
        font-size: 10px;
        opacity: .68;
      }
    `;

    document.head.appendChild(style);
  }

  function folder(id) {
    return document.querySelector(
      `[data-clean-folder="${id}"]`
    );
  }

  function ensureFolderStatus(id) {
    const node = folder(id);
    if (!node) return null;

    let row = node.querySelector(".nb-live-row");

    if (!row) {
      row = document.createElement("span");
      row.className = "nb-live-row";

      row.innerHTML = `
        <span class="nb-live-dot"></span>
        <span class="nb-live-value">
          Connecting…
        </span>
      `;

      node.appendChild(row);
    }

    return row;
  }

  function setFolder(id, text, state = "") {
    const row = ensureFolderStatus(id);
    if (!row) return;

    const dot = row.querySelector(".nb-live-dot");
    const value =
      row.querySelector(".nb-live-value");

    dot.className =
      `nb-live-dot ${state}`.trim();

    value.textContent = text;
  }

  function setItem(module, text) {
    const node = document.querySelector(
      `[data-clean-module="${module}"]`
    );

    if (!node) return;

    let live =
      node.querySelector(".nbcn-item-live");

    if (!live) {
      live = document.createElement("small");
      live.className = "nbcn-item-live";

      const content =
        node.children[1];

      if (content) content.appendChild(live);
    }

    live.textContent = text;
  }

  function prettyPrayer(value) {
    if (!value) return "Unavailable";

    return String(value)
      .replaceAll("_", " ")
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  function formatPrayerTime(value) {
    if (!value) return "";

    const d = new Date(value);

    if (Number.isNaN(d.getTime())) return "";

    return d.toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit"
    });
  }

  function updateFolderPage(data) {
    const {
      home,
      vision,
      presence,
      prayer,
      rules,
      automation,
      runtime,
      health
    } = data;

    if (home) {
      const devices =
        Array.isArray(home.devices)
          ? home.devices
          : [];

      const online =
        devices.filter(x => x.online).length;

      setItem(
        "devices",
        `${online}/${devices.length} online`
      );

      setItem(
        "rooms",
        `${(home.rooms || []).length} rooms`
      );

      setItem(
        "scenes",
        `${(home.scenes || []).length} scenes`
      );
    }

    if (vision) {
      setItem(
        "vision",
        `${vision.status || "unknown"} • ` +
        `${vision.person_count ?? 0} detected`
      );
    }

    if (presence) {
      setItem(
        "presence",
        `${presence.active_count ?? 0} active`
      );
    }

    if (prayer) {
      const time =
        formatPrayerTime(prayer.next_time);

      setItem(
        "prayer",
        `Next: ${prettyPrayer(
          prayer.next_prayer
        )}${time ? " • " + time : ""}`
      );

      setItem(
        "adhan",
        runtime?.runtime?.islamic
          ?.adhan_enabled
          ? "Enabled"
          : "Disabled"
      );

      setItem(
        "prayer-reminders",
        runtime?.runtime?.islamic
          ?.prayer_reminders
          ? "Enabled"
          : "Disabled"
      );
    }

    if (rules) {
      setItem(
        "rules",
        `${rules.rule_count ?? 0} rules`
      );

      setItem(
        "islamic-rules",
        `${rules.rule_count ?? 0} rules`
      );
    }

    if (automation) {
      setItem(
        "automation",
        `${automation.rule_count ?? 0} rules`
      );

      setItem(
        "automation-history",
        `${automation.run_count ?? 0} runs`
      );
    }

    if (runtime?.runtime) {
      const r = runtime.runtime;

      setItem(
        "noor-ai",
        `${r.ai?.local_model || "AI"} • ` +
        `${r.ai?.mode || "unknown"}`
      );

      setItem(
        "settings",
        `${r.assistant?.name || "Noor"} • ` +
        `${r.wakeword_runtime?.status ||
          "unknown"}`
      );

      setItem(
        "privacy-settings",
        `Camera ${
          r.privacy?.camera_enabled
            ? "On"
            : "Off"
        } • Mic ${
          r.privacy?.microphone_enabled
            ? "On"
            : "Off"
        }`
      );

      setItem(
        "notifications",
        r.notifications?.mobile_enabled
          ? "Mobile enabled"
          : "Mobile disabled"
      );
    }

    if (health?.camera) {
      setItem(
        "camera-settings",
        health.camera.connected
          ? "Camera connected"
          : "Camera disconnected"
      );
    }
  }

  async function refresh() {
    if (busy) return;

    busy = true;

    const refreshButton =
      document.getElementById(
        "nbLiveRefreshV12"
      );

    if (refreshButton) {
      refreshButton.disabled = true;
      refreshButton.textContent =
        "Refreshing…";
    }

    try {
      const results = await Promise.allSettled([
        json(API.health),
        json(API.home),
        json(API.vision),
        json(API.presence),
        json(API.prayer),
        json(API.rules),
        json(API.automation),
        json(API.runtime)
      ]);

      const data = {
        health: safe(results[0]),
        home: safe(results[1]),
        vision: safe(results[2]),
        presence: safe(results[3]),
        prayer: safe(results[4]),
        rules: safe(results[5]),
        automation: safe(results[6]),
        runtime: safe(results[7])
      };

      if (data.home) {
        const devices =
          data.home.devices || [];

        const online =
          devices.filter(x => x.online).length;

        setFolder(
          "devices",
          `${online}/${devices.length} devices online`,
          online > 0 ? "ok" : "warn"
        );
      } else {
        setFolder(
          "devices",
          "Unavailable",
          "bad"
        );
      }

      if (data.vision || data.presence) {
        const persons =
          data.presence?.active_count ??
          data.vision?.person_count ??
          0;

        setFolder(
          "ai",
          `Vision live • ${persons} present`,
          data.vision?.status === "healthy"
            ? "ok"
            : "warn"
        );
      } else {
        setFolder(
          "ai",
          "AI status unavailable",
          "bad"
        );
      }

      if (data.automation) {
        setFolder(
          "automation",
          `${data.automation.rule_count ?? 0}` +
          ` rules • ` +
          `${data.automation.run_count ?? 0} runs`,
          data.automation.status === "healthy"
            ? "ok"
            : "warn"
        );
      } else {
        setFolder(
          "automation",
          "Unavailable",
          "bad"
        );
      }

      if (data.prayer) {
        const prayer =
          prettyPrayer(
            data.prayer.next_prayer
          );

        const time =
          formatPrayerTime(
            data.prayer.next_time
          );

        setFolder(
          "islamic",
          `Next ${prayer}` +
          `${time ? " • " + time : ""}`,
          data.prayer.status === "healthy"
            ? "ok"
            : "warn"
        );
      } else {
        setFolder(
          "islamic",
          "Prayer status unavailable",
          "bad"
        );
      }

      if (data.runtime?.runtime) {
        const wake =
          data.runtime.runtime
            .wakeword_runtime;

        setFolder(
          "settings",
          `Noor runtime • ${
            wake?.status || "ready"
          }`,
          data.runtime.status === "ok"
            ? "ok"
            : "warn"
        );
      } else {
        setFolder(
          "settings",
          "Runtime unavailable",
          "bad"
        );
      }

      updateFolderPage(data);

      window.NoorLiveStatusV12.last = data;

    } catch (error) {
      console.error(
        "NOOR LIVE STATUS:",
        error
      );
    } finally {
      busy = false;

      if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.textContent =
          "↻ Live";
      }
    }
  }

  function installRefreshButton() {
    const head =
      document.querySelector(".nbcn-head");

    if (!head) return;

    if (document.getElementById(
      "nbLiveRefreshV12"
    )) return;

    const button =
      document.createElement("button");

    button.id = "nbLiveRefreshV12";
    button.className = "nb-live-refresh";
    button.type = "button";
    button.textContent = "↻ Live";

    button.onclick = event => {
      event.preventDefault();
      event.stopPropagation();
      refresh();
    };

    head.appendChild(button);
  }

  function start() {
    addStyle();

    const wait = setInterval(() => {
      if (!document.getElementById(
        "nbCleanNavV12"
      )) return;

      clearInterval(wait);

      installRefreshButton();

      for (const id of [
        "devices",
        "ai",
        "automation",
        "islamic",
        "settings"
      ]) {
        ensureFolderStatus(id);
      }

      refresh();

      timer = setInterval(
        refresh,
        15000
      );
    }, 100);
  }

  window.NoorLiveStatusV12 = {
    version: "12.1.2",
    refresh,
    last: null,
    stop() {
      if (timer) clearInterval(timer);
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      start,
      { once: true }
    );
  } else {
    start();
  }
})();
