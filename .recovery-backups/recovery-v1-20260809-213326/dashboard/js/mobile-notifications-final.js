(() => {
  "use strict";

  const API = "/api/mobile-notifications";
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json"
      },
      ...options
    });

    const body = await response.json();

    if (!response.ok) {
      throw new Error(
        body.detail || `HTTP ${response.status}`
      );
    }

    return body;
  }

  function mobileHost() {
    return (
      document.getElementById(
        "mobileNotificationsPanel"
      )
      || document.querySelector(".mobile-main")
      || document.querySelector("main")
    );
  }

  function desktopHost() {
    return (
      document.getElementById(
        "page-reminder-rules"
      )
      || document.getElementById(
        "page-halo"
      )
      || document.querySelector("main.main")
      || document.querySelector("main")
    );
  }

  function ensureMobilePanel() {
    const host = mobileHost();

    if (!host) return false;

    if (!$("mobileNotificationFinalPanel")) {
      const panel =
        document.createElement("section");

      panel.id =
        "mobileNotificationFinalPanel";
      panel.className = "mobile-card";
      panel.innerHTML = `
        <h2>Notification Controls</h2>

        <div id="mobileFinalStatus">
          Loading…
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
          <button id="mobileFinalDndToggle">
            Toggle DND
          </button>

          <button id="mobileFinalReactivate">
            Reactivate Snoozed
          </button>

          <button id="mobileFinalRefresh">
            Refresh
          </button>
        </div>
      `;

      host.appendChild(panel);

      $("mobileFinalRefresh")
        ?.addEventListener(
          "click",
          loadStatus,
        );

      $("mobileFinalReactivate")
        ?.addEventListener(
          "click",
          async () => {
            await api(
              "/snoozed/reactivate",
              {method: "POST"}
            );
            await loadStatus();
            window
              .NoorBrainMobileNotifications
              ?.refresh();
          },
        );

      $("mobileFinalDndToggle")
        ?.addEventListener(
          "click",
          toggleDnd,
        );
    }

    return true;
  }

  function ensureDesktopPanel() {
    const host = desktopHost();

    if (!host) return false;

    if (!$("notificationFinalDashboard")) {
      const panel =
        document.createElement("section");

      panel.id =
        "notificationFinalDashboard";
      panel.className = "card";
      panel.innerHTML = `
        <div class="card-head">
          <div>
            <h2>Family & Mobile Intelligence</h2>
            <p>
              Acknowledgements, silent hours,
              snooze and synchronization
            </p>
          </div>

          <button
            id="notificationFinalDashboardRefresh"
            class="button secondary"
          >
            Refresh
          </button>
        </div>

        <div id="notificationFinalDashboardStatus">
          Loading…
        </div>
      `;

      host.appendChild(panel);

      $("notificationFinalDashboardRefresh")
        ?.addEventListener(
          "click",
          loadStatus,
        );
    }

    return true;
  }

  async function toggleDnd() {
    const current =
      await api("/settings");

    await api(
      "/settings",
      {
        method: "PATCH",
        body: JSON.stringify({
          dnd_enabled:
            !current.settings.dnd_enabled
        })
      }
    );

    await loadStatus();
  }

  async function acknowledge(
    notificationId,
    action,
    snoozeMinutes = 10
  ) {
    const result = await api(
      `/${encodeURIComponent(
        notificationId
      )}/acknowledge`,
      {
        method: "POST",
        body: JSON.stringify({
          action,
          snooze_minutes:
            snoozeMinutes
        })
      }
    );

    window
      .NoorBrainMobileNotifications
      ?.refresh();

    await loadStatus();

    return result;
  }

  async function loadStatus() {
    try {
      const status =
        await api("/system-status");

      const text =
        `${status.summary.unread_count} unread · `
        + `${status.summary.total_count} total · `
        + `${status.snoozed_count} snoozed · `
        + `DND ${status.dnd.active ? "active" : "inactive"}`;

      if ($("mobileFinalStatus")) {
        $("mobileFinalStatus")
          .textContent = text;
      }

      if (
        $("notificationFinalDashboardStatus")
      ) {
        $("notificationFinalDashboardStatus")
          .textContent = text;
      }

      if ($("mobileFinalDndToggle")) {
        $("mobileFinalDndToggle")
          .textContent =
          status.dnd.enabled
            ? "Disable DND"
            : "Enable DND";
      }
    } catch (error) {
      if ($("mobileFinalStatus")) {
        $("mobileFinalStatus")
          .textContent =
          `Unavailable: ${error.message}`;
      }

      if (
        $("notificationFinalDashboardStatus")
      ) {
        $("notificationFinalDashboardStatus")
          .textContent =
          `Unavailable: ${error.message}`;
      }
    }
  }

  function enhanceNotificationActions() {
    document
      .querySelectorAll(
        "[data-notification][data-action]"
      )
      .forEach(button => {
        if (
          button.dataset.finalAckBound
          === "true"
        ) {
          return;
        }

        button.dataset.finalAckBound =
          "true";

        const action =
          button.dataset.action;

        button.addEventListener(
          "click",
          async event => {
            event.stopImmediatePropagation();
            event.preventDefault();

            await acknowledge(
              button.dataset.notification,
              action,
              action === "snooze"
                ? 10
                : 0,
            );
          },
          true,
        );
      });
  }

  function mount() {
    const mobileReady =
      ensureMobilePanel();
    const desktopReady =
      ensureDesktopPanel();

    if (
      mobileReady
      || desktopReady
    ) {
      loadStatus();
      enhanceNotificationActions();
    }

    return (
      mobileReady
      || desktopReady
    );
  }

  const observer =
    new MutationObserver(() => {
      mount();
      enhanceNotificationActions();
    });

  observer.observe(
    document.documentElement,
    {
      childList: true,
      subtree: true
    }
  );

  mount();

  window.NoorBrainNotificationFinal = {
    mount,
    refresh: loadStatus,
    acknowledge
  };
})();
