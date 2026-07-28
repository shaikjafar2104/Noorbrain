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

  function ensurePanel() {
    const main =
      document.querySelector(".mobile-main")
      || document.querySelector("main");

    if (!main) return false;

    if (!$("mobileNotificationsPanel")) {
      const panel =
        document.createElement("section");

      panel.id = "mobileNotificationsPanel";
      panel.className = "mobile-card";
      panel.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
          <div>
            <h2>Notifications</h2>
            <p id="mobileNotificationSummary">Loading…</p>
          </div>
          <button id="mobileNotificationPermission">
            Enable Alerts
          </button>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0">
          <select id="mobileNotificationCategory">
            <option value="">All</option>
            <option value="prayer">Prayer</option>
            <option value="islamic_reminder">Islamic reminders</option>
            <option value="greeting">HALO greetings</option>
            <option value="visitor">Visitors</option>
            <option value="automation">Automation</option>
            <option value="general">General</option>
          </select>

          <button id="mobileNotificationUnread">
            Unread
          </button>

          <button id="mobileNotificationReadAll">
            Mark all read
          </button>

          <button id="mobileNotificationRefresh">
            Refresh
          </button>
        </div>

        <div id="mobileNotificationList">
          No notifications.
        </div>
      `;

      main.appendChild(panel);

      $("mobileNotificationRefresh")
        ?.addEventListener(
          "click",
          load,
        );

      $("mobileNotificationCategory")
        ?.addEventListener(
          "change",
          load,
        );

      $("mobileNotificationUnread")
        ?.addEventListener(
          "click",
          () => {
            window.noorNotificationUnreadOnly =
              !window
                .noorNotificationUnreadOnly;
            load();
          },
        );

      $("mobileNotificationReadAll")
        ?.addEventListener(
          "click",
          async () => {
            await api(
              "/actions/mark-all-read",
              {method: "POST"}
            );
            await load();
          },
        );

      $("mobileNotificationPermission")
        ?.addEventListener(
          "click",
          requestPermission,
        );
    }

    return true;
  }

  async function requestPermission() {
    if (!("Notification" in window)) {
      alert(
        "Browser notifications are not supported."
      );
      return;
    }

    const permission =
      await Notification.requestPermission();

    $("mobileNotificationPermission")
      .textContent =
      permission === "granted"
        ? "Alerts Enabled"
        : "Enable Alerts";
  }

  async function performAction(
    notificationId,
    action
  ) {
    await api(
      `/${encodeURIComponent(
        notificationId
      )}/action`,
      {
        method: "POST",
        body: JSON.stringify({action})
      }
    );

    await load();
  }

  function showBrowserAlert(item) {
    if (
      !("Notification" in window)
      || Notification.permission
        !== "granted"
      || item.read
    ) {
      return;
    }

    const key =
      `noor-notification-${item.id}`;

    if (
      sessionStorage.getItem(key)
    ) {
      return;
    }

    new Notification(
      item.title || "NoorBrain",
      {
        body: item.message || "",
        tag: item.id,
        icon:
          "/dashboard-pwa/icons/icon-192.png"
      }
    );

    sessionStorage.setItem(
      key,
      "shown"
    );
  }

  async function load() {
    try {
      const category =
        encodeURIComponent(
          $("mobileNotificationCategory")
            ?.value
          || ""
        );

      const unreadOnly =
        Boolean(
          window
            .noorNotificationUnreadOnly
        );

      const [
        summary,
        result
      ] = await Promise.all([
        api("/summary"),
        api(
          `?limit=100`
          + `&category=${category}`
          + `&unread_only=${unreadOnly}`
        )
      ]);

      $("mobileNotificationSummary")
        .textContent =
        `${summary.unread_count} unread · `
        + `${summary.total_count} total`;

      $("mobileNotificationUnread")
        .textContent =
        unreadOnly
          ? "Show all"
          : "Unread";

      $("mobileNotificationList")
        .innerHTML =
        result.notifications?.length
          ? result.notifications
              .map(item => `
                <article
                  class="mobile-card"
                  style="margin-top:10px;opacity:${item.read ? ".68" : "1"}"
                >
                  <div style="display:flex;justify-content:space-between;gap:10px">
                    <div>
                      <strong>${escapeHtml(item.title)}</strong>
                      <p>${escapeHtml(item.message)}</p>
                      <small>
                        ${escapeHtml(item.category)}
                        · ${new Date(item.created_at).toLocaleString()}
                        · ${escapeHtml(item.status)}
                      </small>
                    </div>
                    <span>
                      ${item.read ? "✓" : "●"}
                    </span>
                  </div>

                  <div class="action-row">
                    <button
                      data-notification="${item.id}"
                      data-action="read"
                    >
                      Read
                    </button>
                    <button
                      data-notification="${item.id}"
                      data-action="completed"
                    >
                      Complete
                    </button>
                    <button
                      data-notification="${item.id}"
                      data-action="snooze"
                    >
                      Snooze
                    </button>
                    <button
                      data-notification="${item.id}"
                      data-action="dismiss"
                    >
                      Dismiss
                    </button>
                  </div>
                </article>
              `).join("")
          : "No notifications.";

      document
        .querySelectorAll(
          "[data-notification][data-action]"
        )
        .forEach(button => {
          button.addEventListener(
            "click",
            () => performAction(
              button.dataset.notification,
              button.dataset.action,
            ),
          );
        });

      result.notifications
        ?.slice(0, 3)
        .forEach(showBrowserAlert);
    } catch (error) {
      $("mobileNotificationSummary")
        .textContent =
        `Notifications unavailable: ${error.message}`;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function mount() {
    const ready = ensurePanel();

    if (ready) load();

    return ready;
  }

  if (!mount()) {
    const observer =
      new MutationObserver(() => {
        if (mount()) {
          observer.disconnect();
        }
      });

    observer.observe(
      document.documentElement,
      {
        childList: true,
        subtree: true
      }
    );

    setTimeout(
      () => observer.disconnect(),
      20000
    );
  }

  window.NoorBrainMobileNotifications = {
    mount,
    refresh: load
  };
})();
