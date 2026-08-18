(() => {
"use strict";

if (window.__NOOR_WEB_CLEAN_V12__) return;
window.__NOOR_WEB_CLEAN_V12__ = true;

const groups = [
  {
    id:"home",
    icon:"⌂",
    title:"Home",
    pages:[
      ["dashboard","Dashboard"],
      ["devices","Devices"],
      ["rooms","Rooms"]
    ]
  },
  {
    id:"ai",
    icon:"✦",
    title:"AI",
    pages:[
      ["vision","Vision AI"],
      ["presence","Presence"],
      ["zones","Vision Zones"],
      ["gallery","Face Identity"],
      ["insights","AI Insights"],
      ["habit-learning","Habit Learning"],
      ["activity","Activity"],
      ["family","Family"]
    ]
  },
  {
    id:"automation",
    icon:"⚡",
    title:"Automation",
    pages:[
      ["smart-automation","Smart Automation"],
      ["scenes","Scenes"],
      ["routines","Routines"],
      ["reminder-rules","Reminder Rules"]
    ]
  },
  {
    id:"islamic",
    icon:"☾",
    title:"Islamic",
    pages:[
      ["prayer-intelligence","Prayer"],
      ["islamic-reminders","Islamic Reminders"],
      ["islamic-rules","Smart Islamic Rules"],
      ["media-library","Media Library"]
    ]
  },
  {
    id:"settings",
    icon:"⚙",
    title:"Settings",
    pages:[
      ["settings","System Settings"],
      ["halo","Noor / HALO"],
      ["halo-voice-runtime","Voice Runtime"],
      ["mobile-notifications","Notifications"],
      ["plugins","Plugins"]
    ]
  }
];

const API = {
  home:"/api/smart-home-runtime/health",
  vision:"/api/vision-intelligence/health",
  presence:"/api/person-presence/health",
  automation:"/api/smart-automation/health",
  prayer:"/api/prayer-intelligence/health",
  runtime:"/api/noor-settings-v11/runtime/status"
};

let refreshTimer = null;

function safe(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

const routedPanels = [
  ["devices", "nbDevicesSection", "Devices", "Manage registered smart-home devices"],
  ["habit-learning", "habitLearningPanel", "Habit Learning", "Patterns and proactive suggestions"],
  ["prayer-intelligence", "prayerIntelligencePanel", "Prayer", "Prayer times and configuration"],
  ["islamic-rules", "nbIslamicV12", "Smart Islamic Rules", "Activity-aware Islamic guidance"],
  ["family", "nbFamilyV11", "Family", "Members, presence and privacy"],
  ["plugins", "nbPluginsV13", "Plugins", "Installed NoorBrain extensions"],
  ["mobile-notifications", "notificationFinalDashboard", "Notifications", "Alerts and delivery settings"]
];

const automationTabs = {
  "smart-automation": "smart",
  scenes: "scenes",
  routines: "routines"
};

function ensureOriginalButton(page, label) {
  const nav = document.querySelector(".sidebar nav");
  if (!nav || existingButton(page)) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "nav-item";
  button.dataset.page = page;
  button.innerHTML = `<span>${label}</span>`;
  nav.appendChild(button);
}

function installProductPages() {
  const main = document.querySelector("main.main");
  const router = window.NoorRouter;
  if (!main || !router) return false;

  routedPanels.forEach(([page, panelId, title, subtitle]) => {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    let pageNode = document.getElementById(`page-${page}`);
    if (!pageNode) {
      pageNode = document.createElement("section");
      pageNode.id = `page-${page}`;
      pageNode.className = "page";
      main.appendChild(pageNode);
    }
    if (panel.parentElement !== pageNode) pageNode.appendChild(panel);
    panel.hidden = false;
    ensureOriginalButton(page, title);
    if (!router.exists(page)) {
      router.register(page, {
        title,
        subtitle,
        onOpen: () => {
          const api = {
            devices: window.NoorDevicesDashboard,
            "habit-learning": window.NoorBrainHabitLearning,
            "prayer-intelligence": window.NoorBrainPrayerIntelligence,
            "islamic-rules": window.NoorBrainIslamicV12,
            family: window.NoorBrainFamilyV11,
            plugins: window.NoorBrainPluginsV13
          }[page];
          api?.refresh?.();
          api?.load?.();
        }
      });
    }
  });

  ensureCameraManager();

  return true;
}

async function cameraRequest(path, options = {}) {
  const response = await fetch(`/api/mobile-v2${path}`, {
    cache: "no-store",
    headers: {"Content-Type": "application/json", ...(options.headers || {})},
    ...options
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}

function ensureCameraManager() {
  const page = document.getElementById("page-vision");
  if (!page || document.getElementById("nbDesktopCameraManager")) return;
  const card = document.createElement("article");
  card.id = "nbDesktopCameraManager";
  card.className = "card";
  card.innerHTML = `
    <div class="card-head"><div><h2>Cameras</h2><p>Registered stream configurations</p></div><button id="nbDesktopCameraAdd" class="button success" type="button">+ Add Camera</button></div>
    <form id="nbDesktopCameraForm" class="ml-form" hidden>
      <label>Name<input id="nbDesktopCameraName" required></label>
      <label>Room<input id="nbDesktopCameraRoom" value="Home" required></label>
      <label>Stream URL<input id="nbDesktopCameraUrl" placeholder="http://camera.local/stream" required></label>
      <div class="ml-actions"><button class="button success" type="submit">Save Camera</button><button id="nbDesktopCameraCancel" class="button secondary" type="button">Cancel</button></div>
    </form>
    <div id="nbDesktopCameraStatus" class="ml-message">Loading cameras…</div>
    <div id="nbDesktopCameraList"></div>`;
  page.appendChild(card);
  document.getElementById("nbDesktopCameraAdd").onclick = () => {
    document.getElementById("nbDesktopCameraForm").hidden = false;
    document.getElementById("nbDesktopCameraName").focus();
  };
  document.getElementById("nbDesktopCameraCancel").onclick = () => {
    document.getElementById("nbDesktopCameraForm").hidden = true;
  };
  document.getElementById("nbDesktopCameraForm").onsubmit = async event => {
    event.preventDefault();
    const status = document.getElementById("nbDesktopCameraStatus");
    try {
      await cameraRequest("/cameras", {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("nbDesktopCameraName").value.trim(),
          room: document.getElementById("nbDesktopCameraRoom").value.trim(),
          stream_url: document.getElementById("nbDesktopCameraUrl").value.trim()
        })
      });
      event.target.reset();
      document.getElementById("nbDesktopCameraRoom").value = "Home";
      event.target.hidden = true;
      await loadDesktopCameras();
    } catch (error) { status.textContent = `Camera save failed: ${error.message}`; }
  };
  document.getElementById("nbDesktopCameraList").onclick = async event => {
    const button = event.target.closest("[data-camera-delete]");
    if (!button || !confirm("Delete this camera configuration?")) return;
    try {
      await cameraRequest(`/cameras/${encodeURIComponent(button.dataset.cameraDelete)}`, {method: "DELETE"});
      await loadDesktopCameras();
    } catch (error) {
      document.getElementById("nbDesktopCameraStatus").textContent = `Camera delete failed: ${error.message}`;
    }
  };
  loadDesktopCameras();
}

async function loadDesktopCameras() {
  const list = document.getElementById("nbDesktopCameraList");
  const status = document.getElementById("nbDesktopCameraStatus");
  if (!list || !status) return;
  try {
    const data = await cameraRequest("/config");
    const cameras = data.config?.cameras || [];
    list.innerHTML = cameras.length ? cameras.map(camera => `
      <div class="nbac-card"><div class="nbac-card-main"><strong>${safe(camera.name)}</strong><small>${safe(camera.room)} · ${safe(camera.stream_url)}</small></div><button class="button danger" type="button" data-camera-delete="${safe(camera.id)}">Delete</button></div>
    `).join("") : `<div class="ml-empty">No additional cameras configured.</div>`;
    status.textContent = `${cameras.length} configured camera(s)`;
  } catch (error) { status.textContent = `Cameras unavailable: ${error.message}`; }
}

function isolateRoutedContent() {
  const main = document.querySelector("main.main");
  if (!main) return;
  [...main.children].forEach(child => {
    if (child.classList.contains("topbar") || child.classList.contains("page")) {
      return;
    }
    child.hidden = true;
    child.dataset.noorProductUnrouted = "1";
  });
}

function style() {
  if (document.getElementById("nbWebCleanStyleV12")) return;

  const s=document.createElement("style");
  s.id="nbWebCleanStyleV12";
  s.textContent=`
    .nb-web-clean {
      padding: 8px 10px 18px;
    }

    .nb-web-clean-title {
      padding: 7px 10px 12px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .12em;
      opacity: .55;
    }

    .nb-web-group {
      margin-bottom: 8px;
      border-radius: 12px;
      overflow: hidden;
    }

    .nb-web-group-head {
      width: 100%;
      border: 0;
      background: transparent;
      color: inherit;
      padding: 10px 11px;
      display: grid;
      grid-template-columns: 25px 1fr auto;
      align-items: center;
      gap: 6px;
      text-align: left;
      cursor: pointer;
      border-radius: 10px;
    }

    .nb-web-group-head:hover {
      background: rgba(255,255,255,.06);
    }

    .nb-web-group-name {
      font-weight: 700;
      font-size: 13px;
    }

    .nb-web-live {
      display: block;
      margin-top: 2px;
      font-size: 9px;
      opacity: .62;
      font-weight: 500;
    }

    .nb-web-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #7f8996;
      display: inline-block;
      margin-right: 5px;
    }

    .nb-web-dot.ok {
      background: #5de58c;
      box-shadow: 0 0 7px rgba(93,229,140,.5);
    }

    .nb-web-dot.warn {
      background: #f1b84c;
    }

    .nb-web-dot.bad {
      background: #ef6b6b;
    }

    .nb-web-arrow {
      font-size: 11px;
      opacity: .55;
    }

    .nb-web-items {
      display: none;
      padding: 2px 5px 8px 34px;
    }

    .nb-web-group.open .nb-web-items {
      display: block;
    }

    .nb-web-sub {
      width: 100%;
      display: block;
      border: 0;
      background: transparent;
      color: inherit;
      text-align: left;
      padding: 8px 9px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 12px;
      opacity: .78;
    }

    .nb-web-sub:hover {
      background: rgba(255,255,255,.06);
      opacity: 1;
    }

    .nb-web-sub.active {
      background: rgba(255,255,255,.09);
      opacity: 1;
      font-weight: 700;
    }

    .nb-web-refresh {
      margin: 8px 10px;
      width: calc(100% - 20px);
      border: 0;
      border-radius: 9px;
      padding: 8px;
      background: rgba(255,255,255,.07);
      color: inherit;
      cursor: pointer;
      font-size: 11px;
    }
  `;
  document.head.appendChild(s);
}

function existingButton(page) {
  return document.querySelector(
    `.sidebar [data-page="${CSS.escape(page)}"]`
  );
}

function activate(page) {
  if (automationTabs[page] && window.NoorAutomationCenterV12?.open) {
    window.NoorAutomationCenterV12.open(automationTabs[page]);
    document.querySelectorAll(".nb-web-sub").forEach(item => {
      item.classList.toggle("active", item.dataset.webPage === page);
    });
    return true;
  }

  installProductPages();
  const button=existingButton(page);

  if (!button) {
    console.warn("NOOR WEB PAGE NOT FOUND:",page);
    return false;
  }

  button.click();
  isolateRoutedContent();

  document.querySelectorAll(".nb-web-sub")
    .forEach(x=>{
      x.classList.toggle(
        "active",
        x.dataset.webPage===page
      );
    });

  return true;
}

function build() {
  const sidebar =
    document.querySelector(".sidebar");

  if (!sidebar) return false;

  const originalNav =
    sidebar.querySelector("nav");

  if (!originalNav) return false;

  if (document.getElementById(
    "nbWebCleanNavV12"
  )) return true;

  /*
   * Keep original router buttons in DOM.
   * Hide only their visual nav container.
   * Existing modules can still find/click them.
   */
  originalNav.style.display="none";
  originalNav.dataset.noorOriginalNav="1";

  const root=document.createElement("div");
  root.id="nbWebCleanNavV12";
  root.className="nb-web-clean";

  root.innerHTML=
    `<div class="nb-web-clean-title">NOORBRAIN</div>`;

  groups.forEach((group,index)=>{
    const wrap=document.createElement("div");
    wrap.className=
      "nb-web-group" +
      (index===0 ? " open" : "");
    wrap.dataset.webGroup=group.id;

    const head=document.createElement("button");
    head.type="button";
    head.className="nb-web-group-head";

    head.innerHTML=`
      <span>${group.icon}</span>
      <span class="nb-web-group-name">
        ${group.title}
        <small class="nb-web-live">
          <span class="nb-web-dot"></span>
          <span class="nb-web-live-text">
            Connecting…
          </span>
        </small>
      </span>
      <span class="nb-web-arrow">›</span>
    `;

    const items=document.createElement("div");
    items.className="nb-web-items";

    group.pages.forEach(([page,label])=>{
      /*
       * Only expose modules that actually
       * exist in current dashboard router.
       */
      if (!existingButton(page) && !automationTabs[page]) return;

      const b=document.createElement("button");
      b.type="button";
      b.className="nb-web-sub";
      b.dataset.webPage=page;
      b.textContent=label;

      b.onclick=()=>{
        activate(page);
      };

      items.appendChild(b);
    });

    head.onclick=()=>{
      wrap.classList.toggle("open");
    };

    wrap.append(head,items);
    root.appendChild(wrap);
  });

  const refresh=document.createElement("button");
  refresh.id="nbWebLiveRefreshV12";
  refresh.type="button";
  refresh.className="nb-web-refresh";
  refresh.textContent="↻ Refresh Live Status";
  refresh.onclick=refreshLive;

  root.appendChild(refresh);

  originalNav.insertAdjacentElement(
    "afterend",
    root
  );

  return true;
}

async function get(url) {
  const c=new AbortController();
  const t=setTimeout(()=>c.abort(),5000);

  try {
    const r=await fetch(url,{
      cache:"no-store",
      signal:c.signal
    });

    if (!r.ok)
      throw new Error(`HTTP ${r.status}`);

    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

function status(group,text,state="") {
  const node=document.querySelector(
    `[data-web-group="${group}"]`
  );

  if (!node) return;

  const dot=node.querySelector(".nb-web-dot");
  const label=node.querySelector(
    ".nb-web-live-text"
  );

  dot.className=`nb-web-dot ${state}`.trim();
  label.textContent=text;
}

function prayerName(v) {
  if (!v) return "Unavailable";

  return String(v)
    .replaceAll("_"," ")
    .replace(/\b\w/g,x=>x.toUpperCase());
}

async function refreshLive() {
  const button=document.getElementById(
    "nbWebLiveRefreshV12"
  );

  if (button) {
    button.disabled=true;
    button.textContent="Refreshing…";
  }

  const result=await Promise.allSettled([
    get(API.home),
    get(API.vision),
    get(API.presence),
    get(API.automation),
    get(API.prayer),
    get(API.runtime)
  ]);

  const value=i=>
    result[i].status==="fulfilled"
      ? result[i].value
      : null;

  const home=value(0);
  const vision=value(1);
  const presence=value(2);
  const automation=value(3);
  const prayer=value(4);
  const runtime=value(5);

  if (home) {
    status(
      "home",
      `${home.device_count ?? 0} devices`,
      home.status==="healthy" ||
      home.status==="ok"
        ? "ok":"warn"
    );
  } else {
    status("home","Unavailable","bad");
  }

  if (vision || presence) {
    status(
      "ai",
      `Vision ${
        vision?.status || "unknown"
      } • ${
        presence?.active_count ?? 0
      } present`,
      vision?.status==="healthy"
        ? "ok":"warn"
    );
  } else {
    status("ai","Unavailable","bad");
  }

  if (automation) {
    status(
      "automation",
      `${automation.rule_count ?? 0} rules • `+
      `${automation.run_count ?? 0} runs`,
      automation.status==="healthy"
        ? "ok":"warn"
    );
  } else {
    status("automation","Unavailable","bad");
  }

  if (prayer) {
    status(
      "islamic",
      `Next ${prayerName(
        prayer.next_prayer
      )}`,
      prayer.status==="healthy"
        ? "ok":"warn"
    );
  } else {
    status("islamic","Unavailable","bad");
  }

  if (runtime) {
    const wake=
      runtime.runtime?.wakeword_runtime;

    status(
      "settings",
      `Runtime ${
        wake?.status ||
        runtime.status ||
        "ready"
      }`,
      runtime.status==="ok"
        ? "ok":"warn"
    );
  } else {
    status("settings","Unavailable","bad");
  }

  if (button) {
    button.disabled=false;
    button.textContent="↻ Refresh Live Status";
  }
}

function observeOriginalRouter() {
  document.addEventListener("click",e=>{
    const target=e.target.closest?.(
      ".sidebar [data-page]"
    );

    if (!target) return;

    const page=target.dataset.page;

    document.querySelectorAll(".nb-web-sub")
      .forEach(x=>{
        x.classList.toggle(
          "active",
          x.dataset.webPage===page
        );
      });
  });
}

function start() {
  style();
  installProductPages();
  isolateRoutedContent();

  let tries=0;

  const wait=setInterval(()=>{
    tries++;

    if (build()) {
      clearInterval(wait);
      observeOriginalRouter();
      refreshLive();

      refreshTimer=setInterval(
        refreshLive,
        15000
      );

      window.setTimeout(() => {
        installProductPages();
        isolateRoutedContent();
      }, 1200);

      window.dispatchEvent(
        new CustomEvent(
          "noor:web-clean-ready"
        )
      );

      return;
    }

    if (tries>100) {
      clearInterval(wait);
      console.error(
        "NOOR WEB CLEAN NAV FAILED TO START"
      );
    }
  },100);
}

window.NoorWebCleanV12={
  version:"12.1.4",
  activate,
  refresh:refreshLive,
  stop(){
    if (refreshTimer)
      clearInterval(refreshTimer);
  }
};

if (document.readyState==="loading") {
  document.addEventListener(
    "DOMContentLoaded",
    start,
    {once:true}
  );
} else {
  start();
}

})();
