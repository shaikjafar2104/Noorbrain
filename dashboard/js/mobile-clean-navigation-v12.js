(() => {
  "use strict";

  if (window.__NOOR_CLEAN_NAV_V12__) return;
  window.__NOOR_CLEAN_NAV_V12__ = true;

  const $ = id => document.getElementById(id);

  const GROUPS = [
    {
      id: "devices",
      icon: "⌂",
      title: "Devices",
      subtitle: "Your home & connected devices",
      items: [
        [
          "devices",
          "💡",
          "All Devices",
          "View and control connected devices"
        ],
        [
          "rooms",
          "⌂",
          "Rooms",
          "Organize devices by room"
        ],
        [
          "groups",
          "◫",
          "Device Groups",
          "Control multiple devices together"
        ],
        [
          "scenes",
          "✦",
          "Scenes",
          "One-tap home states"
        ],
        [
          "add-device",
          "＋",
          "Add Device",
          "Connect a new smart device"
        ]
      ]
    },

    {
      id: "ai",
      icon: "🧠",
      title: "AI",
      subtitle: "Noor & home intelligence",
      items: [
        [
          "noor-ai",
          "✦",
          "Noor AI",
          "Assistant model and behavior"
        ],
        [
          "vision",
          "👁",
          "Vision AI",
          "Camera intelligence"
        ],
        [
          "zones",
          "⌗",
          "Vision Zones",
          "Manage detection areas"
        ],
        [
          "presence",
          "●",
          "Presence",
          "People currently at home"
        ],
        [
          "faces",
          "👤",
          "Face Identity",
          "Family recognition"
        ],
        [
          "habits",
          "🧠",
          "Habit Learning",
          "Learn household routines"
        ],
        [
          "insights",
          "📊",
          "AI Insights",
          "Suggestions and intelligence"
        ]
      ]
    },

    {
      id: "automation",
      icon: "⚡",
      title: "Automation",
      subtitle: "Make NoorBrain act automatically",
      items: [
        [
          "automation",
          "⚡",
          "Smart Rules",
          "Conditions and actions"
        ],
        [
          "rules",
          "✓",
          "Reminder Rules",
          "Presence and activity reminders"
        ],
        [
          "routines",
          "↻",
          "Routines",
          "Scheduled multi-step actions"
        ],
        [
          "schedules",
          "◷",
          "Schedules",
          "Time-based automation"
        ],
        [
          "automation-history",
          "☷",
          "History",
          "Recent automation activity"
        ]
      ]
    },

    {
      id: "islamic",
      icon: "🕌",
      title: "Islamic",
      subtitle: "Prayer, Adhan, Dua & Azkar",
      items: [
        [
          "prayer",
          "🕌",
          "Prayer",
          "Prayer times and intelligence"
        ],
        [
          "adhan",
          "🔊",
          "Adhan",
          "Prayer audio and playback"
        ],
        [
          "prayer-reminders",
          "🔔",
          "Prayer Reminders",
          "Before and after prayer alerts"
        ],
        [
          "reminders",
          "☾",
          "Dua & Azkar",
          "Islamic reminders"
        ],
        [
          "islamic-rules",
          "✓",
          "Islamic Reminder Rules",
          "Activity-aware Islamic guidance"
        ],
        [
          "media",
          "▶",
          "Islamic Media",
          "Dua, Azkar and audio library"
        ]
      ]
    },

    {
      id: "settings",
      icon: "⚙",
      title: "Settings",
      subtitle: "NoorBrain preferences & system",
      items: [
        [
          "settings",
          "✦",
          "Noor & Voice",
          "Assistant, voice and wake words"
        ],
        [
          "notifications",
          "📱",
          "Notifications",
          "Phone and dashboard alerts"
        ],
        [
          "family",
          "👨‍👩‍👧‍👦",
          "Family",
          "Profiles and household members"
        ],
        [
          "privacy-settings",
          "◉",
          "Privacy",
          "Camera, microphone and learning"
        ],
        [
          "camera-settings",
          "📷",
          "Camera Settings",
          "Camera and vision preferences"
        ],
        [
          "network-settings",
          "⌁",
          "Network & Devices",
          "Connectivity and device services"
        ],
        [
          "advanced-settings",
          "⚙",
          "Advanced",
          "Diagnostics and developer options"
        ]
      ]
    }
  ];

  function style() {
    if ($("nbCleanNavStyleV12")) return;

    const el = document.createElement("style");
    el.id = "nbCleanNavStyleV12";

    el.textContent = `
      #nbv2Modules {
        display: none !important;
      }

      #nbCleanNavV12 {
        margin: 18px 0 100px;
      }

      .nbcn-head {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
      }

      .nbcn-head small {
        display: block;
        opacity: .55;
        font-size: 10px;
        letter-spacing: .12em;
      }

      .nbcn-head h2 {
        margin: 3px 0 0;
        font-size: 21px;
      }

      .nbcn-folders {
        display: grid;
        grid-template-columns:
          repeat(2, minmax(0,1fr));
        gap: 10px;
      }

      .nbcn-folder {
        min-height: 108px;
        border: 1px solid rgba(255,255,255,.07);
        border-radius: 17px;
        padding: 15px;
        text-align: left;
        color: #f6f9fd;
        background:
          linear-gradient(
            145deg,
            rgba(26,57,91,.95),
            rgba(13,35,60,.95)
          );
        box-shadow:
          0 8px 24px rgba(0,0,0,.12);
      }

      .nbcn-folder:active {
        transform: scale(.98);
      }

      .nbcn-folder-icon {
        display: block;
        font-size: 25px;
        margin-bottom: 14px;
      }

      .nbcn-folder b,
      .nbcn-folder small {
        display: block;
      }

      .nbcn-folder b {
        font-size: 15px;
      }

      .nbcn-folder small {
        margin-top: 3px;
        opacity: .57;
        line-height: 1.3;
      }

      #nbCleanFolderV12 {
        position: fixed;
        inset: 0;
        z-index: 2147482500;
        background:
          linear-gradient(180deg,#0c2037,#071522);
        color: white;
        overflow: auto;
      }

      .nbcn-page {
        max-width: 760px;
        min-height: 100vh;
        margin: auto;
      }

      .nbcn-page-head {
        position: sticky;
        top: 0;
        z-index: 4;
        display: grid;
        grid-template-columns: auto 1fr;
        align-items: center;
        gap: 13px;
        padding: 16px;
        background: rgba(8,24,41,.96);
        backdrop-filter: blur(15px);
        border-bottom:
          1px solid rgba(255,255,255,.07);
      }

      .nbcn-back {
        width: 42px;
        height: 42px;
        border: 0;
        border-radius: 12px;
        background: #193653;
        color: white;
        font-size: 27px;
      }

      .nbcn-page-head small {
        display: block;
        opacity: .5;
        font-size: 10px;
        letter-spacing: .12em;
      }

      .nbcn-page-head h2 {
        margin: 2px 0 0;
        font-size: 20px;
      }

      .nbcn-items {
        display: grid;
        gap: 9px;
        padding: 15px;
      }

      .nbcn-item {
        display: grid;
        grid-template-columns: 45px 1fr 24px;
        align-items: center;
        gap: 10px;
        width: 100%;
        border: 1px solid rgba(255,255,255,.07);
        border-radius: 15px;
        padding: 13px;
        background: #102942;
        color: white;
        text-align: left;
      }

      .nbcn-item-icon {
        display: grid;
        place-items: center;
        width: 42px;
        height: 42px;
        border-radius: 12px;
        background: rgba(255,255,255,.06);
        font-size: 20px;
      }

      .nbcn-item b,
      .nbcn-item small {
        display: block;
      }

      .nbcn-item b {
        font-size: 14px;
      }

      .nbcn-item small {
        margin-top: 3px;
        opacity: .55;
        font-size: 11px;
      }

      .nbcn-arrow {
        opacity: .4;
        font-size: 20px;
      }

      @media(max-width:360px) {
        .nbcn-folders {
          grid-template-columns: 1fr;
        }
      }
    `;

    document.head.appendChild(el);
  }

  function createFolderPage() {
    if ($("nbCleanFolderV12")) return;

    const page = document.createElement("section");
    page.id = "nbCleanFolderV12";
    page.hidden = true;

    page.innerHTML = `
      <div class="nbcn-page">
        <header class="nbcn-page-head">
          <button
            id="nbcnBack"
            class="nbcn-back"
            type="button">‹</button>

          <div>
            <small id="nbcnPageLabel">NOORBRAIN</small>
            <h2 id="nbcnPageTitle">Menu</h2>
          </div>
        </header>

        <main
          id="nbcnItems"
          class="nbcn-items">
        </main>
      </div>
    `;

    document.body.appendChild(page);

    $("nbcnBack").onclick = closeFolder;

    $("nbcnItems").addEventListener(
      "click",
      event => {
        const item =
          event.target.closest("[data-clean-module]");

        if (!item) return;

        const module =
          item.dataset.cleanModule;

        closeFolder();

        setTimeout(() => {
          const original =
            document.querySelector(
              `[data-module="${CSS.escape(module)}"]`
            );

          if (original) {
            original.click();
            return;
          }

          document.dispatchEvent(
            new CustomEvent(
              "noor:v12-module",
              { detail: { module } }
            )
          );
        }, 30);
      }
    );
  }

  function openFolder(id) {
    const group =
      GROUPS.find(x => x.id === id);

    if (!group) return;

    $("nbcnPageLabel").textContent =
      "NOORBRAIN " + group.title.toUpperCase();

    $("nbcnPageTitle").textContent =
      group.title;

    $("nbcnItems").innerHTML =
      group.items.map(
        ([module, icon, title, subtitle]) => `
          <button
            class="nbcn-item"
            type="button"
            data-clean-module="${module}">
            <span class="nbcn-item-icon">
              ${icon}
            </span>

            <span>
              <b>${title}</b>
              <small>${subtitle}</small>
            </span>

            <span class="nbcn-arrow">›</span>
          </button>
        `
      ).join("");

    $("nbCleanFolderV12").hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeFolder() {
    const page = $("nbCleanFolderV12");

    if (page) page.hidden = true;

    document.body.style.overflow = "";
  }

  function createNavigation() {
    if ($("nbCleanNavV12")) return;

    const old =
      document.querySelector("#nbv2Modules");

    if (!old) {
      console.error(
        "V12 CLEAN NAV: old module section missing"
      );
      return;
    }

    const section =
      document.createElement("section");

    section.id = "nbCleanNavV12";

    section.innerHTML = `
      <div class="nbcn-head">
        <div>
          <small>CONTROL CENTER</small>
          <h2>Explore NoorBrain</h2>
        </div>
      </div>

      <div class="nbcn-folders">
        ${GROUPS.map(group => `
          <button
            class="nbcn-folder"
            type="button"
            data-clean-folder="${group.id}">

            <span class="nbcn-folder-icon">
              ${group.icon}
            </span>

            <b>${group.title}</b>
            <small>${group.subtitle}</small>
          </button>
        `).join("")}
      </div>
    `;

    old.insertAdjacentElement(
      "afterend",
      section
    );

    section.addEventListener(
      "click",
      event => {
        const folder =
          event.target.closest(
            "[data-clean-folder]"
          );

        if (!folder) return;

        openFolder(
          folder.dataset.cleanFolder
        );
      }
    );
  }

  function clickExisting(module) {
    const button =
      document.querySelector(
        `[data-module="${CSS.escape(module)}"]`
      );

    if (!button) return false;

    button.click();
    return true;
  }


  function openSettings() {
    if (window.NoorMobileSettingsV11?.open) {
      window.NoorMobileSettingsV11.open();
      return true;
    }

    return false;
  }


  function openStudio(hash) {
    location.href =
      `/studio#${encodeURIComponent(hash)}`;
  }


  function routeExtra(module) {
    switch (module) {

      case "rooms":
        if (!clickExisting("devices")) {
          openStudio("devices");
        }
        return;

      case "groups":
        openStudio("smart-home");
        return;

      case "scenes":
        openStudio("smart-home");
        return;

      case "add-device": {
        const add =
          document.querySelector("#nbv2AddDevice");

        if (add) {
          add.click();
        } else {
          openStudio("devices");
        }
        return;
      }

      case "noor-ai":
        openSettings();
        return;

      case "camera":
        if (document.getElementById("nbv2CameraSection")) {
          document.getElementById("nbv2CameraSection").scrollIntoView({
            behavior: "smooth",
            block: "start"
          });
        } else if (window.NoorBrainDashboardCamera?.refresh) {
          window.NoorBrainDashboardCamera.refresh();
        } else {
          openStudio("vision");
        }
        return;

      case "activity":
        if (document.querySelector("[data-page='activity']")) {
          document.querySelector("[data-page='activity']").click();
        } else if (window.NoorBrainActivityIntelligence?.openPage) {
          window.NoorBrainActivityIntelligence.openPage();
        } else {
          openStudio("activity");
        }
        return;

      case "routines":
        if (window.NoorAutomationCenterV12?.open) {
          window.NoorAutomationCenterV12.open("smart");
        } else {
          openStudio("smart-automation");
        }
        return;

      case "schedules":
        if (window.NoorAutomationCenterV12?.open) {
          window.NoorAutomationCenterV12.open("smart");
        } else {
          openStudio("smart-automation");
        }
        return;

      case "automation-history":
        if (window.NoorAutomationCenterV12?.open) {
          window.NoorAutomationCenterV12.open("smart");
        } else {
          openStudio("smart-automation");
        }
        return;

      case "adhan":
        if (!clickExisting("prayer")) {
          openStudio("prayer-intelligence");
        }
        return;

      case "prayer-reminders":
        if (!clickExisting("prayer")) {
          openStudio("prayer-intelligence");
        }
        return;

      case "islamic-rules":
        if (window.NoorMobileRulesV12?.open) {
          window.NoorMobileRulesV12.open();
        } else {
          openStudio("reminder-rules");
        }
        return;

      case "privacy-settings":
      case "camera-settings":
      case "network-settings":
      case "advanced-settings":
        openSettings();
        return;

      default:
        if (!clickExisting(module)) {
          console.warn(
            "V12 navigation target unavailable:",
            module
          );
        }
    }
  }

  document.addEventListener(
    "noor:v12-module",
    event => {
      routeExtra(event.detail?.module);
    }
  );

  function start() {
    style();
    createFolderPage();
    createNavigation();

    window.NoorCleanNavigationV12 =
      Object.freeze({
        installed: true,
        version: "12.1.1",
        openFolder,
        closeFolder
      });

    console.log(
      "NOOR_CLEAN_NAVIGATION_V12_READY"
    );
  }

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
