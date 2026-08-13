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
      ["activity","Activity"]
    ]
  },
  {
    id:"automation",
    icon:"⚡",
    title:"Automation",
    pages:[
      ["smart-automation","Smart Automation"],
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
      ["halo-voice-runtime","Voice Runtime"]
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
  const button=existingButton(page);

  if (!button) {
    console.warn("NOOR WEB PAGE NOT FOUND:",page);
    return false;
  }

  button.click();

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
      if (!existingButton(page)) return;

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
      if (
        group.id === "automation" &&
        window.NoorAutomationCenterV12?.open
      ) {
        window.NoorAutomationCenterV12.open("smart");
        return;
      }

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
