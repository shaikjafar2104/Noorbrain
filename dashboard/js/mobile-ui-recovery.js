(() => {
  "use strict";

  const API = "/api/ui-recovery";
  const $ = id => document.getElementById(id);

  let deferredPrompt = null;

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json"
      },
      ...options
    });

    const contentType =
      response.headers.get("content-type") || "";

    const body =
      contentType.includes("application/json")
        ? await response.json()
        : {detail: await response.text()};

    if (!response.ok) {
      throw new Error(
        body.detail || `HTTP ${response.status}`
      );
    }

    return body;
  }

  function removeBrokenControlPanel() {
    const old = $("mobileNotificationFinalPanel");

    if (old) {
      old.hidden = true;
      old.style.display = "none";
      old.setAttribute("aria-hidden", "true");
    }
  }

  function ensureControlPanel() {
    removeBrokenControlPanel();

    const notifications =
      $("mobileNotificationsPanel");
    const host =
      notifications
      || document.querySelector(".mobile-main")
      || document.querySelector("main");

    if (!host) return false;

    if (!$("nbMobileControlPanel")) {
      const panel =
        document.createElement("section");

      panel.id = "nbMobileControlPanel";
      panel.className =
        "mobile-card nb-mobile-control-card";

      panel.innerHTML = `
        <div class="nb-mobile-section-head">
          <div>
            <h2>Notification Controls</h2>
            <p id="nbMobileControlStatus">
              Loading…
            </p>
          </div>

          <span
            id="nbMobileDndBadge"
            class="nb-mobile-pill"
          >
            DND
          </span>
        </div>

        <div class="nb-mobile-control-grid">
          <button id="nbMobileDndToggle">
            Enable DND
          </button>

          <button id="nbMobileReadAll">
            Mark all read
          </button>

          <button id="nbMobileReactivate">
            Reactivate snoozed
          </button>

          <button id="nbMobileRefresh">
            Refresh all
          </button>
        </div>
      `;

      if (notifications) {
        notifications.insertAdjacentElement(
          "afterend",
          panel
        );
      } else {
        host.appendChild(panel);
      }

      $("nbMobileDndToggle")
        ?.addEventListener(
          "click",
          toggleDnd,
        );

      $("nbMobileReadAll")
        ?.addEventListener(
          "click",
          markAllRead,
        );

      $("nbMobileReactivate")
        ?.addEventListener(
          "click",
          reactivateSnoozed,
        );

      $("nbMobileRefresh")
        ?.addEventListener(
          "click",
          refreshAll,
        );
    }

    return true;
  }

  async function loadStatus() {
    const status =
      $("nbMobileControlStatus");

    if (!status) return;

    status.textContent = "Refreshing…";

    try {
      const result = await api(
        "/mobile/status"
      );

      status.textContent =
        `${result.summary.unread_count} unread`
        + ` · ${result.summary.total_count} total`
        + ` · ${result.snoozed_count} snoozed`;

      const badge =
        $("nbMobileDndBadge");
      const toggle =
        $("nbMobileDndToggle");

      if (badge) {
        badge.textContent =
          result.dnd.active
            ? "DND Active"
            : result.dnd.enabled
              ? "DND Scheduled"
              : "DND Off";

        badge.classList.toggle(
          "is-active",
          result.dnd.active
        );
      }

      if (toggle) {
        toggle.textContent =
          result.dnd.enabled
            ? "Disable DND"
            : "Enable DND";
      }
    } catch (error) {
      status.textContent =
        `Controls unavailable: ${error.message}`;
    }
  }

  async function toggleDnd() {
    setBusy(
      $("nbMobileDndToggle"),
      true,
      "Updating…"
    );

    try {
      await api(
        "/mobile/toggle-dnd",
        {method: "POST"}
      );

      await loadStatus();
      showNotice(
        "DND setting updated."
      );
    } catch (error) {
      showNotice(
        `DND failed: ${error.message}`,
        true
      );
    } finally {
      setBusy(
        $("nbMobileDndToggle"),
        false
      );
    }
  }

  async function markAllRead() {
    setBusy(
      $("nbMobileReadAll"),
      true,
      "Updating…"
    );

    try {
      await api(
        "/mobile/mark-all-read",
        {method: "POST"}
      );

      await refreshAll();
      showNotice(
        "All notifications marked read."
      );
    } catch (error) {
      showNotice(
        `Update failed: ${error.message}`,
        true
      );
    } finally {
      setBusy(
        $("nbMobileReadAll"),
        false
      );
    }
  }

  async function reactivateSnoozed() {
    setBusy(
      $("nbMobileReactivate"),
      true,
      "Checking…"
    );

    try {
      const result = await api(
        "/mobile/reactivate-snoozed",
        {method: "POST"}
      );

      await refreshAll();

      showNotice(
        `${result.reactivated_count}`
        + " snoozed notification(s)"
        + " reactivated."
      );
    } catch (error) {
      showNotice(
        `Reactivate failed: ${error.message}`,
        true
      );
    } finally {
      setBusy(
        $("nbMobileReactivate"),
        false
      );
    }
  }

  async function refreshAll() {
    const button =
      $("nbMobileRefresh");

    setBusy(
      button,
      true,
      "Refreshing…"
    );

    try {
      await Promise.allSettled([
        loadStatus(),
        window
          .NoorBrainMobileNotifications
          ?.refresh?.(),
      ]);

      const baseRefresh =
        window.NoorBrainMobileApp
          ?.refresh;

      if (
        typeof baseRefresh === "function"
      ) {
        await baseRefresh();
      }

      showNotice(
        "Mobile app refreshed."
      );
    } finally {
      setBusy(button, false);
    }
  }

  function setBusy(
    button,
    busy,
    text
  ) {
    if (!button) return;

    if (busy) {
      button.dataset.originalText =
        button.textContent;
      button.disabled = true;
      button.textContent =
        text || "Working…";
    } else {
      button.disabled = false;

      if (
        button.dataset.originalText
      ) {
        button.textContent =
          button.dataset.originalText;
      }
    }
  }

  function showNotice(
    message,
    error = false
  ) {
    let notice =
      $("nbMobileNotice");

    if (!notice) {
      notice =
        document.createElement("div");
      notice.id =
        "nbMobileNotice";
      document.body.appendChild(
        notice
      );
    }

    notice.className =
      `nb-mobile-notice ${
        error ? "error" : "success"
      }`;
    notice.textContent = message;

    clearTimeout(
      window.nbMobileNoticeTimer
    );

    requestAnimationFrame(() => {
      notice.classList.add("show");
    });

    window.nbMobileNoticeTimer =
      setTimeout(() => {
        notice.classList.remove(
          "show"
        );
      }, 2800);
  }

  function setupInstall() {
    const button = $("installApp");

    if (!button) return;

    button.hidden = false;
    button.textContent = "Install";

    window.addEventListener(
      "beforeinstallprompt",
      event => {
        event.preventDefault();
        deferredPrompt = event;
        button.textContent =
          "Install App";
      }
    );

    button.addEventListener(
      "click",
      async event => {
        event.preventDefault();
        event.stopImmediatePropagation();

        if (deferredPrompt) {
          deferredPrompt.prompt();
          await deferredPrompt.userChoice;
          deferredPrompt = null;
          return;
        }

        const secure =
          window.isSecureContext
          || location.hostname === "localhost"
          || location.hostname === "127.0.0.1";

        if (!secure) {
          showInstallHelp(
            "For direct app installation, open NoorBrain over HTTPS. On Android Chrome, use the browser menu and choose “Add to Home screen”."
          );
          return;
        }

        showInstallHelp(
          "Open the browser menu and choose “Install app” or “Add to Home screen”."
        );
      },
      true,
    );

    window.addEventListener(
      "appinstalled",
      () => {
        button.textContent =
          "Installed";
        button.disabled = true;
      }
    );
  }

  function showInstallHelp(message) {
    let dialog =
      $("nbInstallHelp");

    if (!dialog) {
      dialog =
        document.createElement("div");

      dialog.id = "nbInstallHelp";
      dialog.className =
        "nb-install-help";

      dialog.innerHTML = `
        <div class="nb-install-help-card">
          <h3>Install NoorBrain</h3>
          <p id="nbInstallHelpText"></p>
          <button id="nbInstallHelpClose">
            Close
          </button>
        </div>
      `;

      document.body.appendChild(
        dialog
      );

      $("nbInstallHelpClose")
        ?.addEventListener(
          "click",
          () => dialog.remove(),
        );
    }

    $("nbInstallHelpText")
      .textContent = message;
  }

  function enhanceNavigation() {
    const nav =
      document.querySelector(
        ".mobile-nav"
      );

    if (!nav) return;

    nav.innerHTML = `
      <button data-nb-mobile-target="top">
        <span>⌂</span>
        Home
      </button>

      <button data-nb-mobile-target="haloText">
        <span>◉</span>
        HALO
      </button>

      <button data-nb-mobile-target="mobileNotificationsPanel">
        <span>●</span>
        Alerts
      </button>

      <a href="/studio">
        <span>◫</span>
        Studio
      </a>
    `;

    nav
      .querySelectorAll(
        "[data-nb-mobile-target]"
      )
      .forEach(button => {
        button.addEventListener(
          "click",
          () => {
            const target =
              button.dataset.nbMobileTarget;

            if (target === "top") {
              window.scrollTo({
                top: 0,
                behavior: "smooth"
              });
              return;
            }

            const element =
              $(target);

            element?.scrollIntoView({
              behavior: "smooth",
              block: "start"
            });

            if (
              element
              && (
                element.tagName === "INPUT"
                || element.tagName === "TEXTAREA"
              )
            ) {
              setTimeout(
                () => element.focus(),
                350
              );
            }
          }
        );
      });
  }

  function repairNotificationButtons() {
    const refresh =
      $("mobileNotificationRefresh");

    if (
      refresh
      && refresh.dataset
        .nbRecoveryBound !== "true"
    ) {
      refresh.dataset.nbRecoveryBound =
        "true";

      refresh.addEventListener(
        "click",
        refreshAll,
        true,
      );
    }

    const readAll =
      $("mobileNotificationReadAll");

    if (
      readAll
      && readAll.dataset
        .nbRecoveryBound !== "true"
    ) {
      readAll.dataset.nbRecoveryBound =
        "true";

      readAll.addEventListener(
        "click",
        markAllRead,
        true,
      );
    }
  }

  function mount() {
    removeBrokenControlPanel();

    const ready =
      ensureControlPanel();

    setupInstall();
    enhanceNavigation();
    repairNotificationButtons();

    if (ready) {
      loadStatus();
    }

    return ready;
  }

  const observer =
    new MutationObserver(() => {
      removeBrokenControlPanel();

      if (ensureControlPanel()) {
        repairNotificationButtons();
        observer.disconnect();
        loadStatus();
      }
    });

  if (mount()) {
    observer.disconnect();
  } else {
    observer.observe(
      document.documentElement,
      {
        childList: true,
        subtree: true
      }
    );
  }

  window.NoorBrainMobileUIRecovery = {
    mount,
    refresh: refreshAll
  };
})();
