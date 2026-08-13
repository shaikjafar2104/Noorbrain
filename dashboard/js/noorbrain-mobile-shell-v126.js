(()=>{
"use strict";

const VERSION="12.6.0";

const TABS={
  home:{
    title:"Home",
    icon:"⌂"
  },
  automation:{
    title:"Automation",
    icon:"◇"
  },
  halo:{
    title:"HALO",
    icon:"◉"
  },
  islamic:{
    title:"Islamic",
    icon:"☾"
  },
  more:{
    title:"More",
    icon:"☰"
  }
};

const $=id=>document.getElementById(id);
let v126HaloBusy=false;

function esc(v){
  return String(v??"")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;");
}

function getNativeBackTarget(defaultTab="home"){
  return (
    document.body.dataset.nb126BackTarget ||
    window.NoorBrainV126ModuleBridge?.lastTab ||
    defaultTab
  );
}

function setNativeBackTarget(target="home"){
  document.body.dataset.nb126BackTarget = target || "home";
  return target || "home";
}

function nb126PageHeader({
  title,
  subtitle="",
  showBack=false,
  backTarget="home",
  rightAction=""
}={}){
  const backHtml = showBack ? `
    <button
      type="button"
      class="nb126-back-button"
      data-nb126-back="${esc(backTarget || "home")}" 
      aria-label="Back to ${esc(backTarget || "home")}"
    >
      ‹
    </button>
  ` : "";

  const actionHtml = rightAction ? `
    <div class="nb126-header-action">
      ${rightAction}
    </div>
  ` : "";

  return `
    <header class="nb126-page-header">
      <div class="nb126-page-header-inner">
        ${backHtml}
        <div class="nb126-page-header-copy">
          <small>NOORBRAIN</small>
          <h1>${esc(title || "NoorBrain")}</h1>
          ${subtitle ? `<p>${esc(subtitle)}</p>` : ""}
        </div>
        ${actionHtml}
      </div>
    </header>
  `;
}

function bindNativeBackButtons(container=document){
  const content = container && container.querySelector ? container : document;
  content.querySelectorAll("[data-nb126-back]").forEach(button => {
    if (button.dataset.nb126BackBound === "1") return;
    button.dataset.nb126BackBound = "1";
    button.addEventListener("click", () => {
      const target = button.dataset.nb126Back || getNativeBackTarget("home");
      const bridge = window.NoorBrainV126ModuleBridge || V126_MODULE_BRIDGE;
      bridge.lastTab = target;
      bridge.close();
    });
  });
}

/* Parent mapping and active tab helpers */
const V126_PARENT_MAP = {
  camera: "home",
  devices: "home",
  "add-device": "more",
  zones: "home",
  activity: "halo",
  "automation-center": "automation",
  scenes: "automation",
  routines: "automation",
  prayer: "islamic",
  media: "islamic",
  "islamic-rules": "islamic",
  notifications: "more",
  settings: "more"
};

function setActiveTab(tabName){
  if(!tabName) tabName = getNativeBackTarget("home");
  document.querySelectorAll("#noorbrainMobile126 [data-nb126-route]")
    .forEach(b=>b.classList.toggle("active", b.dataset.nb126Route===tabName));
  window.NoorBrainV126ModuleBridge = window.NoorBrainV126ModuleBridge || V126_MODULE_BRIDGE;
  window.NoorBrainV126ModuleBridge.lastTab = tabName;
}

function tile({
  icon,
  title,
  text,
  action,
  badge=""
}){
  return `
    <button
      class="nb126-tile"
      type="button"
      data-nb126-action="${esc(action)}"
    >
      <span class="nb126-tile-icon">${icon}</span>

      <span class="nb126-tile-copy">
        <strong>${esc(title)}</strong>
        <small>${esc(text)}</small>
      </span>

      ${badge
        ? `<span class="nb126-badge">${esc(badge)}</span>`
        : ""
      }

      <span class="nb126-chevron">›</span>
    </button>
  `;
}

function home(){
  return `
    <section class="nb126-hero">
      <div>
        <small>NOORBRAIN HOME</small>
        <h1>Assalamu Alaikum</h1>
        <p>
          Your private smart home and Islamic assistant.
        </p>
      </div>

      <button
        class="nb126-profile"
        data-nb126-route="more"
        type="button"
      >
        SJ
      </button>
    </section>

    <section class="nb126-section">
      <div class="nb126-section-title">
        <h2>Quick Access</h2>
      </div>

      <div class="nb126-grid">
        ${tile({
          icon:"◉",
          title:"HALO",
          text:"Ask NoorBrain",
          action:"halo"
        })}

        ${tile({
          icon:"⌂",
          title:"Devices",
          text:"Control your home",
          action:"devices"
        })}

        ${tile({
          icon:"▣",
          title:"Camera",
          text:"Live home view",
          action:"camera"
        })}

        ${tile({
          icon:"◇",
          title:"Automation",
          text:"Rules & routines",
          action:"automation"
        })}
      </div>
    </section>

    <section class="nb126-section">
      <div class="nb126-section-title">
        <h2>Islamic</h2>
      </div>

      <div class="nb126-grid">
        ${tile({
          icon:"☾",
          title:"Prayer",
          text:"Prayer intelligence",
          action:"prayer"
        })}

        ${tile({
          icon:"♫",
          title:"Dua & Azkar",
          text:"Your Islamic audio",
          action:"media"
        })}

        ${tile({
          icon:"✦",
          title:"Smart Islamic Rules",
          text:"Activity-aware reminders",
          action:"islamic-rules"
        })}

        ${tile({
          icon:"▦",
          title:"Zones",
          text:"Rooms & camera zones",
          action:"zones"
        })}
      </div>
    </section>
  `;
}

function automation(){
  return `
    <section class="nb126-page-head">
      <small>SMART HOME</small>
      <h1>Automation</h1>
      <p>
        Make NoorBrain react automatically to your home.
      </p>
    </section>

    <section class="nb126-section">
      <div class="nb126-grid">
        ${tile({
          icon:"✦",
          title:"Smart Rules",
          text:"Triggers and actions",
          action:"automation-center"
        })}

        ${tile({
          icon:"▶",
          title:"Scenes",
          text:"Run multiple actions",
          action:"scenes"
        })}

        ${tile({
          icon:"↻",
          title:"Routines",
          text:"Daily automations",
          action:"routines"
        })}

        ${tile({
          icon:"⌂",
          title:"Rooms & Zones",
          text:"Manage your spaces",
          action:"zones"
        })}

        ${tile({
          icon:"▣",
          title:"Devices",
          text:"Connected smart devices",
          action:"devices"
        })}

        ${tile({
          icon:"☾",
          title:"Islamic Rules",
          text:"Dua, Azkar & reminders",
          action:"islamic-rules"
        })}
      </div>
    </section>
  `;
}

function halo(){
  return `
    <section class="nb126-halo">

      <div class="nb126-halo-copy">
        <small>NOORBRAIN AI</small>
        <h1>HALO</h1>
        <p>
          Voice control for your home and Islamic assistant.
        </p>
      </div>

      <button
        type="button"
        class="nb126-orb"
        data-nb126-action="halo-live"
        aria-label="Talk to HALO"
      >
        <span></span>
        <b>◉</b>
      </button>

      <strong class="nb126-halo-prompt">
        Tap to talk
      </strong>

      <div class="nb126-card">
        <label for="nb126HaloInput">Ask Noor</label>
        <textarea
          id="nb126HaloInput"
          class="nb126-input"
          rows="3"
          placeholder="Ask Noor about your home or an Islamic question…"
          data-halo-input
        ></textarea>
        <button
          type="button"
          class="nb126-button nb126-button-primary nb126-full"
          data-nb126-action="halo-send"
        >
          Send
        </button>
        <small id="nb126HaloStatus" data-halo-reply>
          Ready for your question.
        </small>
      </div>

    </section>

    <section class="nb126-section">
      <div class="nb126-grid">
        ${tile({
          icon:"⌂",
          title:"Control Home",
          text:"Lights, devices & scenes",
          action:"devices"
        })}

        ${tile({
          icon:"☾",
          title:"Islamic Assistant",
          text:"Prayer, Dua & Azkar",
          action:"islamic"
        })}

        ${tile({
          icon:"◇",
          title:"Automations",
          text:"Manage smart actions",
          action:"automation"
        })}

        ${tile({
          icon:"▣",
          title:"Activity",
          text:"Home activity intelligence",
          action:"activity"
        })}
      </div>
    </section>
  `;
}

function islamic(){
  return `
    <section class="nb126-page-head">
      <small>ISLAMIC HOME</small>
      <h1>Islamic</h1>
      <p>
        Prayer, Dua, Azkar and intelligent reminders.
      </p>
    </section>

    <section class="nb126-section">
      <div class="nb126-grid">
        ${tile({
          icon:"◷",
          title:"Prayer Times",
          text:"Prayer intelligence",
          action:"prayer"
        })}

        ${tile({
          icon:"♫",
          title:"Dua & Azkar",
          text:"Islamic Media Library",
          action:"media"
        })}

        ${tile({
          icon:"✦",
          title:"Smart Islamic Rules",
          text:"Play audio by activity",
          action:"islamic-rules"
        })}

        ${tile({
          icon:"⌂",
          title:"Room Reminders",
          text:"Zone-aware guidance",
          action:"zones"
        })}

        ${tile({
          icon:"◉",
          title:"Ask HALO",
          text:"Islamic voice assistant",
          action:"halo"
        })}
      </div>
    </section>
  `;
}

function more(){
  return `
    <section class="nb126-page-head">
      <small>NOORBRAIN</small>
      <h1>More</h1>
      <p>
        Home setup, personalization and settings.
      </p>
    </section>

    <section class="nb126-list">
      ${tile({
        icon:"+",
        title:"Add Device",
        text:"Connect a smart home device",
        action:"add-device"
      })}

      ${tile({
        icon:"⌂",
        title:"Rooms & Zones",
        text:"Create and rename spaces",
        action:"zones"
      })}

      ${tile({
        icon:"▣",
        title:"Camera & Vision",
        text:"Presence and detection",
        action:"camera"
      })}

      ${tile({
        icon:"♫",
        title:"Media Library",
        text:"Manage your audio",
        action:"media"
      })}

      ${tile({
        icon:"⚙",
        title:"Settings",
        text:"NoorBrain preferences",
        action:"settings"
      })}
    </section>
  `;
}

const renderers={
  home,
  automation,
  halo,
  islamic,
  more
};


function logV126(tag, payload={}) {
  const entry = {
    tag,
    ts: Date.now(),
    ...payload
  };
  console.log("V126_" + tag, entry);
  return entry;
}

const V126_MODULE_BRIDGE={
  lastTab:"home",
  module:null,

  open(module){
    this.lastTab =
      document.body.dataset.nb126Page || "home";

    this.module=module;

    logV126("BRIDGE",{
      module,
      mode:"existing-mobile-router"
    });

    /*
     * IMPORTANT:
     * Never navigate V12.6 to /studio.
     * The Android app must stay on /mobile.
     *
     * Reuse the existing mobile product router.
     */
    if (module && TABS[module]) {
      navigate(module, true);
      logV126("RESULT", {
        module,
        router: "v126-native-tab",
        handled: true
      });
      return true;
    }

    if(window.NoorMobileProductRouterV12?.open){
      const handled =
        window.NoorMobileProductRouterV12.open(module);

      logV126("RESULT",{
        module,
        router:"NoorMobileProductRouterV12",
        handled:!!handled
      });

      if(handled){
        return true;
      }
    }

    /*
     * Existing legacy mobile module buttons are
     * allowed as a compatibility fallback.
     */
    const selectors=[
      `[data-module="${module}"]`,
      `[data-action="${module}"]`,
      `[data-route="${module}"]`
    ];

    for(const selector of selectors){
      const target=document.querySelector(selector);

      if(
        target &&
        !target.closest("#noorbrainMobile126")
      ){
        target.click();

        logV126("RESULT",{
          module,
          fallback:selector,
          handled:true
        });

        return true;
      }
    }

    logV126("RESULT",{
      module,
      handled:false
    });

    return false;
  },

  close(){
    this.module=null;

    navigate(
      this.lastTab || "home",
      false
    );

    return true;
  }
};


async function openV126Zones(){
  const content=document.getElementById("nb126Content");
  if(!content) return false;

  content.innerHTML=`
    <section class="nb126-page">
      ${nb126PageHeader({
        title: "Rooms & Zones",
        subtitle: "Camera detection areas",
        showBack: true,
        backTarget: getNativeBackTarget("home")
      })}

      <div class="nb126-page-body">
        <div id="nb126ZonesList" class="nb126-grid">
          <div class="nb126-card nb126-state-card">
            <b>Loading zones…</b>
          </div>
        </div>
      </div>
    </section>
  `;

  bindNativeBackButtons(content);
  document.body.dataset.nb126Page="zones";

  document.querySelectorAll(
    "#noorbrainMobile126 [data-nb126-route]"
  ).forEach(button=>{
    button.classList.remove("active");
  });

  const list=document.getElementById("nb126ZonesList");

  try{
    let response=await fetch(
      "/api/vision-zones/zones",
      {cache:"no-store"}
    );

    let payload=await response.json();

    if(!response.ok){
      throw new Error("HTTP "+response.status);
    }

    const zones=Array.isArray(payload)
      ? payload
      : (payload.zones || []);

    if(!zones.length){
      list.innerHTML=`
        <div class="nb126-card">
          <b>No zones configured</b>
          <small>Create zones from the NoorBrain dashboard.</small>
        </div>
      `;
      return true;
    }

    list.innerHTML=zones.map(zone=>`
      <div class="nb126-card">
        <div>
          <small>ZONE</small>
          <h3>${esc(zone.name || "Unnamed Zone")}</h3>
          <p>
            ${zone.enabled === false ? "Disabled" : "Active"}
            ${zone.camera_id ? " • "+esc(zone.camera_id) : ""}
          </p>
        </div>
      </div>
    `).join("");

    logV126("RESULT",{
      action:"zones",
      mode:"native-v126",
      count:zones.length,
      ok:true
    });

    return true;

  }catch(error){
    list.innerHTML=`
      <div class="nb126-card">
        <b>Zones unavailable</b>
        <small>${esc(error.message)}</small>
      </div>
    `;

    console.error("V126_ZONES_ERROR",error);
    return false;
  }
}


async function openV126Activity(){
  const content=document.getElementById("nb126Content");
  if(!content) return false;

  content.innerHTML=`
    <section class="nb126-page">
      ${nb126PageHeader({
        title: "Activity",
        subtitle: "Real home presence and movement events",
        showBack: true,
        backTarget: getNativeBackTarget("home")
      })}

      <div class="nb126-page-body">
        <div id="nb126ActivitySummary" class="nb126-card nb126-state-card">
          <b>Loading activity…</b>
        </div>

        <div id="nb126ActivityList" class="nb126-grid">
        </div>
      </div>
    </section>
  `;

  bindNativeBackButtons(content);
  document.body.dataset.nb126Page="activity";

  document.querySelectorAll(
    "#noorbrainMobile126 [data-nb126-route]"
  ).forEach(button=>{
    button.classList.remove("active");
  });

  const summary=document.getElementById(
    "nb126ActivitySummary"
  );

  const list=document.getElementById(
    "nb126ActivityList"
  );

  try{
    let response=await fetch(
      "/api/activity/activities?limit=20",
      {cache:"no-store"}
    );

    if(!response.ok){
      response=await fetch(
        "/api/activity-intelligence/events?limit=20",
        {cache:"no-store"}
      );
    }

    if(!response.ok){
      response=await fetch(
        "/activity/events?limit=20",
        {cache:"no-store"}
      );
    }

    if(!response.ok){
      throw new Error("Activity API unavailable");
    }

    const payload=await response.json();

    const events=Array.isArray(payload)
      ? payload
      : (
          payload.events ||
          payload.items ||
          payload.activity ||
          []
        );

    summary.innerHTML=`
      <b>${events.length} recent event${events.length===1?"":"s"}</b>
      <small>Live NoorBrain activity data</small>
    `;

    if(!events.length){
      list.innerHTML=`
        <div class="nb126-card">
          <b>No recent activity</b>
          <small>New camera/presence events will appear here.</small>
        </div>
      `;
      return true;
    }

    list.innerHTML=events.map(event=>{
      const type=
        event.event_type ||
        event.type ||
        event.event ||
        "activity";

      const zone=
        event.zone ||
        event.zone_name ||
        "";

      const person=
        event.person_name ||
        event.person_id ||
        "";

      const time=
        event.time_text ||
        event.timestamp ||
        event.created_at ||
        "";

      return `
        <div class="nb126-card">
          <div>
            <small>${esc(type)}</small>
            <h3>${esc(zone || "Home")}</h3>
            <p>
              ${person ? "Person: "+esc(person)+"<br>" : ""}
              ${time ? esc(time) : ""}
            </p>
          </div>
        </div>
      `;
    }).join("");

    logV126("RESULT",{
      action:"activity",
      mode:"native-v126",
      count:events.length,
      ok:true
    });

    return true;

  }catch(error){
    summary.innerHTML=`
      <b>Activity unavailable</b>
      <small>${esc(error.message)}</small>
    `;

    list.innerHTML="";

    console.error(
      "V126_ACTIVITY_ERROR",
      error
    );

    return false;
  }
}


function openV126Camera(){
  const content=document.getElementById("nb126Content");

  if(!content){
    console.error("V126_CAMERA_ERROR content missing");
    return false;
  }

  document.body.dataset.nb126Page="camera";

  document.querySelectorAll(
    "#noorbrainMobile126 [data-nb126-route]"
  ).forEach(button=>{
    button.classList.remove("active");
  });

  content.innerHTML=`
    <section class="nb126-page">
      ${nb126PageHeader({
        title: "Camera",
        subtitle: "Live NoorBrain camera",
        showBack: true,
        backTarget: getNativeBackTarget("home")
      })}

      <div class="nb126-page-body">
        <div class="nb126-card nb126-camera-frame"
             style="padding:0;overflow:hidden">

        <div style="
          position:relative;
          width:100%;
          background:#000;
          min-height:220px;
        ">

          <img
            id="nb126LiveCamera"
            src="/camera_live?v=${Date.now()}"
            alt="NoorBrain Live Camera"
            style="
              display:block;
              width:100%;
              height:auto;
              min-height:220px;
              object-fit:contain;
              background:#000;
            "
          >

          <div
            id="nb126CameraState"
            style="
              position:absolute;
              left:12px;
              bottom:12px;
              padding:6px 10px;
              border-radius:999px;
              background:rgba(0,0,0,.65);
              font-size:12px;
            "
          >
            Connecting…
          </div>

        </div>
      </div>

        <div class="nb126-grid">

          <button
            class="nb126-card nb126-action-card"
            type="button"
            id="nb126CameraRefresh"
          >
            <div>
              <small>CAMERA</small>
              <h3>Refresh Stream</h3>
              <p>Reconnect to the live camera</p>
            </div>
          </button>

          <button
            class="nb126-card nb126-action-card"
            type="button"
            data-nb126-action="zones"
          >
            <div>
              <small>VISION</small>
              <h3>Rooms & Zones</h3>
              <p>View camera detection zones</p>
            </div>
          </button>

        </div>
      </div>

    </section>
  `;

  bindNativeBackButtons(content);

  const img=document.getElementById(
    "nb126LiveCamera"
  );

  const state=document.getElementById(
    "nb126CameraState"
  );

  const refresh=document.getElementById(
    "nb126CameraRefresh"
  );

  const load=()=>{
    state.textContent="Connecting…";

    img.src=
      "/camera_live?v="+Date.now();
  };

  img.addEventListener("load",()=>{
    state.textContent="LIVE";

    console.log(
      "V126_CAMERA_LIVE",
      img.naturalWidth,
      img.naturalHeight
    );
  });

  img.addEventListener("error",()=>{
    state.textContent="Camera unavailable";

    console.error(
      "V126_CAMERA_ERROR",
      img.src
    );
  });

  refresh.addEventListener(
    "click",
    load
  );

  console.log(
    "V126_CAMERA_OPEN",
    "/camera_live"
  );

  return true;
}



/* =========================================================
   V12.6 FINAL NATIVE FEATURE SCREENS
   Camera / Activity / Zones are intentionally NOT modified.
   ========================================================= */

function nb126Page(title,subtitle,body,{showBack=false, backTarget="home", rightAction=""}={}){
  const content=document.getElementById("nb126Content");
  if(!content) return false;

  const resolvedBackTarget = backTarget || getNativeBackTarget("home");
  document.body.dataset.nb126Page = title.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  document.querySelectorAll(
    "#noorbrainMobile126 [data-nb126-route]"
  ).forEach(b=>b.classList.remove("active"));

  /* Keep the parent tab active when rendering a secondary page */
  setActiveTab(getNativeBackTarget());

  content.innerHTML=`
    <section class="nb126-page">
      ${nb126PageHeader({
        title,
        subtitle: subtitle || "",
        showBack,
        backTarget: resolvedBackTarget,
        rightAction
      })}
      <div class="nb126-page-body">
        ${body}
      </div>
    </section>
  `;

  const backButton = content.querySelector("[data-nb126-back]");
  backButton?.addEventListener("click", () => {
    const target = backButton.dataset.nb126Back || resolvedBackTarget;
    const bridge = window.NoorBrainV126ModuleBridge || V126_MODULE_BRIDGE;
    bridge.lastTab = target;
    bridge.close();
  });

  return true;
}

function nb126Loading(title,subtitle){
  return nb126Page(
    title,
    subtitle,
    `<div class="nb126-card">
       <b>Loading…</b>
     </div>`
  );
}

async function nb126Fetch(url,options){
  const supplied=options||{};
  const controller=(
    !supplied.signal && "AbortController" in window
  ) ? new AbortController() : null;
  const timeout=controller
    ? window.setTimeout(()=>controller.abort(),30000)
    : null;
  let response;

  try{
    response=await fetch(
      url,
      Object.assign(
        {cache:"no-store"},
        supplied,
        controller ? {signal:controller.signal} : {}
      )
    );
  }catch(error){
    if(error?.name==="AbortError"){
      throw new Error("Request timed out. Check the NoorBrain connection.");
    }
    throw error;
  }finally{
    if(timeout!==null) window.clearTimeout(timeout);
  }

  let data=null;

  try{
    data=await response.json();
  }catch(_){
    data={};
  }

  if(!response.ok){
    throw new Error(
      (data && (data.detail||data.message)) ||
      "HTTP "+response.status
    );
  }

  return data;
}

function nb126Empty(title,text){
  return `
    <div class="nb126-card">
      <b>${esc(title)}</b>
      <small>${esc(text)}</small>
    </div>
  `;
}


/* DEVICES */

async function openV126Devices(){
  nb126Loading(
    "Devices",
    "Connected NoorBrain devices"
  );

  try{
    const d=await nb126Fetch("/api/devices");

    const devices=Array.isArray(d)
      ? d
      : (d.devices||[]);

    const onlineCount=devices.filter(device=>device.online===true).length;

    const cards=devices.length
      ? devices.map(device=>`
          <button
            class="nb126-card"
            type="button"
            data-v126-device-toggle="${esc(device.id||"")}"
            ${device.online===true ? "" : "disabled"}
          >
            <div>
              <small>${esc(device.device_type||device.type||"DEVICE")}</small>
              <h3>${esc(device.name||device.id||"Device")}</h3>
              <p>
                ${esc(device.room||"Home")}
                •
                ${esc(String(
                  device.state ??
                  device.status ??
                  "unknown"
                ))}
                •
                ${device.online===true ? "Online" : "Offline"}
              </p>
            </div>
          </button>
        `).join("")
      : nb126Empty(
          "No devices connected",
          "Pair a real device to control it here."
        );

    nb126Page(
      "Devices",
      `${devices.length} registered • ${onlineCount} online`,
      `
        <div class="nb126-grid">${cards}</div>

        <button
          class="nb126-card"
          id="v126AddDevice"
          type="button"
        >
          <div>
            <small>SETUP</small>
            <h3>＋ Add Device</h3>
            <p>Register a real device configuration</p>
          </div>
        </button>
      `
    );

    document.getElementById("v126AddDevice")
      ?.addEventListener("click",openV126AddDevice);

    document.querySelectorAll(
      "[data-v126-device-toggle]"
    ).forEach(button=>{
      button.addEventListener("click",async()=>{
        const id=button.dataset.v126DeviceToggle;
        if(!id) return;

        button.disabled=true;

        try{
          await nb126Fetch(
            "/api/devices/"+encodeURIComponent(id)+"/toggle",
            {
              method:"POST",
              headers:{"Content-Type":"application/json"},
              body:"{}"
            }
          );

          await openV126Devices();
        }catch(error){
          alert("Device control failed: "+error.message);
          button.disabled=false;
        }
      });
    });

    return true;

  }catch(error){
    nb126Page(
      "Devices",
      "Connected NoorBrain devices",
      nb126Empty(
        "Devices unavailable",
        error.message
      )
    );
    return false;
  }
}


/* ADD DEVICE */

function openV126AddDevice(){
  nb126Page(
    "Add Device",
    "Register a real device",
    `
      <div class="nb126-card">
        <small>DEVICE SETUP</small>
        <h3>New device</h3>

        <label>
          Name
          <input
            id="v126DeviceName"
            placeholder="Living Room Light"
          >
        </label>

        <label>
          Type
          <select id="v126DeviceType">
            <option value="light">Light</option>
            <option value="fan">Fan</option>
            <option value="plug">Plug</option>
            <option value="relay">Relay</option>
            <option value="switch">Switch</option>
            <option value="sensor">Sensor</option>
            <option value="camera">Camera</option>
            <option value="other">Other</option>
          </select>
        </label>

        <label>
          Room
          <input
            id="v126DeviceRoom"
            placeholder="Living Room"
          >
        </label>

        <label>
          Transport
          <select id="v126DeviceProtocol">
            <option value="logical">Not configured</option>
            <option value="http">HTTP / ESP32</option>
            <option value="mqtt">MQTT</option>
          </select>
        </label>

        <label>
          IP address or base URL
          <input
            id="v126DeviceAddress"
            placeholder="192.168.1.50"
          >
        </label>

        <label>
          MQTT command topic
          <input
            id="v126DeviceTopic"
            placeholder="home/living-room/light/set"
          >
        </label>

        <button
          id="v126DeviceCreate"
          type="button"
        >
          Register Device
        </button>

        <small>
          Registration does not claim the device is online. NoorBrain only
          changes state after a configured transport executes successfully.
        </small>
        <small id="v126DeviceMessage"></small>
      </div>
    `
  );

  document.getElementById("v126DeviceCreate")
    ?.addEventListener("click",async()=>{
      const name=document.getElementById(
        "v126DeviceName"
      ).value.trim();

      const type=document.getElementById(
        "v126DeviceType"
      ).value.trim();

      const room=document.getElementById(
        "v126DeviceRoom"
      ).value.trim();

      const protocol=document.getElementById(
        "v126DeviceProtocol"
      ).value;

      const address=document.getElementById(
        "v126DeviceAddress"
      ).value.trim();

      const commandTopic=document.getElementById(
        "v126DeviceTopic"
      ).value.trim();

      const msg=document.getElementById(
        "v126DeviceMessage"
      );

      if(!name){
        msg.textContent="Device name is required.";
        return;
      }

      try{
        await nb126Fetch(
          "/api/devices",
          {
            method:"POST",
            headers:{
              "Content-Type":"application/json"
            },
            body:JSON.stringify({
              name,
              device_type:type||"other",
              room:room||"Home",
              online:false,
              ip_address:
                address && !address.includes("://")
                  ? address
                  : null,
              metadata:{
                protocol,
                base_url:
                  address.includes("://")
                    ? address
                    : null,
                command_topic:commandTopic||null
              }
            })
          }
        );

        await openV126Devices();

      }catch(error){
        msg.textContent=error.message;
      }
    });

  return true;
}


/* SCENES */

async function openV126Scenes(){
  nb126Loading(
    "Scenes",
    "Whole-home actions"
  );

  try{
    const d=await nb126Fetch(
      "/api/automation/scenes"
    );

    const items=d.scenes||[];

    nb126Page(
      "Scenes",
      `${items.length} scene${items.length===1?"":"s"}`,
      `<div class="nb126-grid">
        ${
          items.length
          ? items.map(x=>`
              <button
                class="nb126-card"
                type="button"
                data-v126-scene="${esc(x.id||"")}"
              >
                <div>
                  <small>SCENE</small>
                  <h3>${esc(x.name||"Scene")}</h3>
                  <p>Tap to execute</p>
                </div>
              </button>
            `).join("")
          : nb126Empty(
              "No scenes configured",
              "Scenes you create will appear here."
            )
        }
      </div>`
    );

    document.querySelectorAll(
      "[data-v126-scene]"
    ).forEach(button=>{
      button.addEventListener("click",async()=>{
        try{
          await nb126Fetch(
            "/api/automation/scenes/"+
            encodeURIComponent(button.dataset.v126Scene)+
            "/execute",
            {method:"POST"}
          );
          alert("Scene executed.");
        }catch(error){
          alert("Scene failed: "+error.message);
        }
      });
    });

    return true;

  }catch(error){
    nb126Page(
      "Scenes",
      "Whole-home actions",
      nb126Empty("Scenes unavailable",error.message)
    );
    return false;
  }
}


/* ROUTINES */

async function openV126Routines(){
  nb126Loading(
    "Routines",
    "Scheduled home actions"
  );

  try{
    const d=await nb126Fetch(
      "/api/automation/routines"
    );

    const items=d.routines||[];

    nb126Page(
      "Routines",
      `${items.length} routine${items.length===1?"":"s"}`,
      `<div class="nb126-grid">
        ${
          items.length
          ? items.map(x=>`
              <button
                class="nb126-card"
                type="button"
                data-v126-routine="${esc(x.id||"")}"
              >
                <div>
                  <small>ROUTINE</small>
                  <h3>${esc(x.name||"Routine")}</h3>
                  <p>Tap to run</p>
                </div>
              </button>
            `).join("")
          : nb126Empty(
              "No routines configured",
              "Routines you create will appear here."
            )
        }
      </div>`
    );

    document.querySelectorAll(
      "[data-v126-routine]"
    ).forEach(button=>{
      button.addEventListener("click",async()=>{
        try{
          await nb126Fetch(
            "/api/automation/routines/"+
            encodeURIComponent(button.dataset.v126Routine)+
            "/run",
            {method:"POST"}
          );
          alert("Routine started.");
        }catch(error){
          alert("Routine failed: "+error.message);
        }
      });
    });

    return true;

  }catch(error){
    nb126Page(
      "Routines",
      "Scheduled home actions",
      nb126Empty(
        "Routines unavailable",
        error.message
      )
    );
    return false;
  }
}


/* SMART AUTOMATION */

async function openV126AutomationRules(){
  nb126Loading(
    "Smart Rules",
    "NoorBrain automation engine"
  );

  try{
    const [smart, reminderReply] = await Promise.all([
      nb126Fetch("/api/smart-automation/rules").catch(() => ({ rules: [] })),
      nb126Fetch("/reminder-rules").catch(() => ({ rules: [] }))
    ]);

    const smartRules = Array.isArray(smart?.rules) ? smart.rules : [];
    const reminderRules = Array.isArray(reminderReply?.rules) ? reminderReply.rules : [];
    const rules = smartRules.length ? smartRules : reminderRules;

    nb126Page(
      "Smart Rules",
      `${rules.length} automation rule${rules.length===1?"":"s"}`,
      `<div class="nb126-grid">
        ${
          rules.length
          ? rules.map(rule=>`
              <div class="nb126-card">
                <small>${rule.source === "reminder" ? "REMINDER" : "SMART RULE"}</small>
                <h3>${esc(rule.name || rule.title || "Automation")}</h3>
                <p>
                  ${rule.enabled===false ? "Disabled" : "Enabled"}
                  ${rule.zone ? " • "+esc(rule.zone) : ""}
                  ${rule.trigger ? " • "+esc(rule.trigger) : ""}
                </p>
              </div>
            `).join("")
          : nb126Empty(
              "No smart automation rules",
              "The automation engine is ready."
            )
        }
      </div>`
    );

    return true;

  }catch(error){
    nb126Page(
      "Smart Rules",
      "NoorBrain automation engine",
      nb126Empty(
        "Automation unavailable",
        error.message
      )
    );
    return false;
  }
}


/* PRAYER */

async function openV126Prayer(){
  nb126Loading(
    "Prayer",
    "Prayer intelligence"
  );

  try{
    const [times,status]=await Promise.all([
      nb126Fetch("/api/prayer-intelligence/times"),
      nb126Fetch("/api/prayer-intelligence/status")
    ]);

    const t=times.times||{};

    const rows=Object.entries(t)
      .map(([name,time])=>`
        <div class="nb126-card">
          <small>PRAYER</small>
          <h3>${esc(name)}</h3>
          <p>${esc(String(time))}</p>
        </div>
      `).join("");

    nb126Page(
      "Prayer",
      status.next_prayer
        ? `Next: ${status.next_prayer} • ${status.next_time||""}`
        : "Today's prayer times",
      `<div class="nb126-grid">
        ${rows || nb126Empty(
          "Prayer times unavailable",
          "No prayer times returned."
        )}
      </div>`
    );

    return true;

  }catch(error){
    nb126Page(
      "Prayer",
      "Prayer intelligence",
      nb126Empty(
        "Prayer unavailable",
        error.message
      )
    );
    return false;
  }
}


/* DUA & AZKAR / MEDIA */

async function openV126Media(){
  nb126Loading(
    "Dua & Azkar",
    "Islamic audio library"
  );

  try{
    const d=await nb126Fetch("/api/media");
    const items=d.items||[];

    nb126Page(
      "Dua & Azkar",
      `${items.length} media item${items.length===1?"":"s"}`,
      `<div class="nb126-grid">
        ${
          items.length
          ? items.map(item=>`
              <button
                class="nb126-card"
                type="button"
                data-v126-media="${esc(item.id||"")}"
              >
                <div>
                  <small>${esc(item.category||"MEDIA")}</small>
                  <h3>${esc(item.name||"Audio")}</h3>
                  <p>Tap to play</p>
                </div>
              </button>
            `).join("")
          : nb126Empty(
              "No Islamic media",
              "Your media library is empty."
            )
        }
      </div>`
    );

    document.querySelectorAll(
      "[data-v126-media]"
    ).forEach(button=>{
      button.addEventListener("click",async()=>{
        const mediaId = button.dataset.v126Media;
        if(!mediaId) return;

        try{
          const audio = new Audio(
            `/api/media/${encodeURIComponent(mediaId)}/file?ts=${Date.now()}`
          );
          audio.volume = 1;

          const results=await Promise.allSettled([
            audio.play(),
            nb126Fetch(
              `/api/media/${encodeURIComponent(mediaId)}/play`,
              {method:"POST", cache:"no-store"}
            )
          ]);

          if(results.every(result=>result.status==="rejected")){
            throw new Error(
              results.map(result=>result.reason?.message)
                .filter(Boolean).join(" • ") || "Audio playback failed."
            );
          }

        }catch(error){
          alert("Playback failed: "+error.message);
        }
      });
    });

    return true;

  }catch(error){
    nb126Page(
      "Dua & Azkar",
      "Islamic audio library",
      nb126Empty(
        "Media unavailable",
        error.message
      )
    );
    return false;
  }
}


/* ISLAMIC REMINDER RULES */

async function openV126IslamicRules(){
  nb126Loading(
    "Smart Islamic Rules",
    "Activity-aware Islamic reminders"
  );

  try{
    const d=await nb126Fetch(
      "/reminder-rules"
    );

    const rules=d.rules||[];

    nb126Page(
      "Smart Islamic Rules",
      `${rules.length} reminder rule${rules.length===1?"":"s"}`,
      `<div class="nb126-grid">
        ${
          rules.length
          ? rules.map(rule=>`
              <button
                class="nb126-card"
                type="button"
                data-v126-rule-toggle="${esc(rule.id||"")}"
                data-v126-rule-enabled="${rule.enabled===false ? "false" : "true"}"
              >
                <div>
                  <small>
                    ${rule.enabled===false?"DISABLED":"ACTIVE"}
                  </small>

                  <h3>${esc(rule.name||"Islamic Rule")}</h3>

                  <p>
                    ${esc(rule.trigger||"")}
                    ${rule.zone ? " • "+esc(rule.zone) : ""}
                  </p>
                </div>
              </button>
            `).join("")
          : nb126Empty(
              "No Islamic reminder rules",
              "Create a reminder rule to begin."
            )
        }
      </div>`
    );

    document.querySelectorAll(
      "[data-v126-rule-toggle]"
    ).forEach(button=>{
      button.addEventListener("click",async()=>{
        try{
          const enabled = button.dataset.v126RuleEnabled !== "true";

          await nb126Fetch(
            "/reminder-rules/"+
            encodeURIComponent(button.dataset.v126RuleToggle)+
            "/toggle",
            {
              method:"PATCH",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({enabled})
            }
          );

          await openV126IslamicRules();

        }catch(error){
          alert("Rule update failed: "+error.message);
        }
      });
    });

    return true;

  }catch(error){
    nb126Page(
      "Smart Islamic Rules",
      "Activity-aware Islamic reminders",
      nb126Empty(
        "Rules unavailable",
        error.message
      )
    );
    return false;
  }
}


/* NOTIFICATIONS */

async function openV126Notifications(){
  nb126Loading(
    "Notifications",
    "NoorBrain alerts"
  );

  const candidates=[
    "/api/mobile-notifications",
    "/api/mobile-notifications/summary"
  ];

  let data=null;
  let used="";

  for(const url of candidates){
    try{
      data=await nb126Fetch(url);
      used=url;
      break;
    }catch(_){}
  }

  if(!data){
    nb126Page(
      "Notifications",
      "NoorBrain alerts",
      nb126Empty(
        "Notifications unavailable",
        "Notification service did not return data."
      )
    );
    return false;
  }

  const items=
    data.notifications ||
    data.items ||
    [];

  nb126Page(
    "Notifications",
    `${items.length} notification${items.length===1?"":"s"}`,
    `<div class="nb126-grid">
      ${
        items.length
        ? items.map(n=>`
            <div class="nb126-card">
              <small>NOTIFICATION</small>
              <h3>${esc(n.title||n.name||"NoorBrain")}</h3>
              <p>${esc(n.message||n.body||"")}</p>
            </div>
          `).join("")
        : nb126Empty(
            "No notifications",
            "Nothing needs your attention."
          )
      }
    </div>`
  );

  console.log(
    "V126_NOTIFICATIONS_SOURCE",
    used
  );

  return true;
}


/* SETTINGS */

async function openV126Settings(){
  nb126Page(
    "Settings",
    "NoorBrain mobile settings",
    `
      <div class="nb126-grid">

        <button
          class="nb126-card"
          type="button"
          data-nb126-action="notifications"
        >
          <div>
            <small>ALERTS</small>
            <h3>Notifications</h3>
            <p>View NoorBrain alerts</p>
          </div>
        </button>

        <div class="nb126-card">
          <small>SYSTEM</small>
          <h3>NoorBrain</h3>
          <p>Connected to the live NoorBrain backend.</p>
        </div>

        <div class="nb126-card">
          <small>V12.6</small>
          <h3>Native Mobile UI</h3>
          <p>Camera, Activity and Zones remain protected.</p>
        </div>

      </div>
    `
  );

  return true;
}



/* =========================================================
   V126_A42_FUNCTIONAL_FINISHING
   Devices / Smart Rules / Scenes / Routines

   Protected:
   openV126Camera()
   openV126Activity()
   openV126Zones()
   ========================================================= */

function v126A42Text(value,fallback=""){
  if(value===null || value===undefined){
    return fallback;
  }
  return String(value);
}

function v126A42Array(payload,key){
  if(Array.isArray(payload)) return payload;
  if(payload && Array.isArray(payload[key])){
    return payload[key];
  }
  return [];
}

function v126A42FriendlyError(error){
  console.error("V126_A42_ERROR",error);

  return (
    error &&
    error.message &&
    !String(error.message).startsWith("HTTP ")
  )
    ? error.message
    : "NoorBrain could not complete this request.";
}

function v126A42Status(enabled){
  return enabled===false
    ? `<span class="nb126-badge nb126-badge-warning">
         Disabled
       </span>`
    : `<span class="nb126-badge nb126-badge-success">
         Active
       </span>`;
}

function v126A42Empty(title,text,actionHtml=""){
  return `
    <div class="nb126-empty">
      <div class="nb126-empty-icon">◇</div>
      <h3>${esc(title)}</h3>
      <p>${esc(text)}</p>
      ${actionHtml}
    </div>
  `;
}

function v126A42Error(title,error,retryAction){
  return `
    <div class="nb126-error">
      <h3>${esc(title)}</h3>
      <p>${esc(v126A42FriendlyError(error))}</p>

      <button
        type="button"
        class="nb126-button nb126-button-secondary"
        data-nb126-action="${esc(retryAction)}"
      >
        Retry
      </button>
    </div>
  `;
}


/* ---------------------------------------------------------
   DEVICES
   --------------------------------------------------------- */

async function openV126DevicesA42(){
  nb126Loading(
    "Devices",
    "Your connected NoorBrain devices"
  );

  try{
    const payload=await nb126Fetch("/api/devices");

    const devices=v126A42Array(
      payload,
      "devices"
    );

    const body=devices.length
      ? `
        <div class="nb126-section">
          <div class="nb126-section-title">
            <div>
              <small>SMART HOME</small>
              <h2>Connected Devices</h2>
            </div>

            <span class="nb126-badge">
              ${devices.length}
            </span>
          </div>

          <div class="nb126-list">
            ${devices.map(device=>{
              const id=v126A42Text(device.id);
              const name=v126A42Text(
                device.name,
                "Unnamed Device"
              );

              const room=v126A42Text(
                device.room ||
                device.zone ||
                device.location,
                "Home"
              );

              const type=v126A42Text(
                device.type ||
                device.device_type,
                "Device"
              );

              const state=v126A42Text(
                device.state ??
                device.status ??
                "unknown"
              );

              return `
                <div class="nb126-list-row">
                  <div class="nb126-list-main">
                    <small>${esc(type)}</small>
                    <h3>${esc(name)}</h3>
                    <p>
                      ${esc(room)}
                      •
                      ${esc(state)}
                    </p>
                  </div>

                  ${
                    id
                    ? `
                      <button
                        type="button"
                        class="
                          nb126-button
                          nb126-button-secondary
                          nb126-device-control
                        "
                        data-v126-a42-device="${esc(id)}"
                      >
                        Toggle
                      </button>
                    `
                    : ""
                  }
                </div>
              `;
            }).join("")}
          </div>
        </div>

        <button
          type="button"
          class="nb126-button nb126-button-primary nb126-full"
          data-nb126-action="add-device"
        >
          ＋ Add Device
        </button>
      `
      : v126A42Empty(
          "No devices connected",
          "Connect your first real NoorBrain device to control it from here.",
          `
            <button
              type="button"
              class="nb126-button nb126-button-primary"
              data-nb126-action="add-device"
            >
              ＋ Add Device
            </button>
          `
        );

    nb126Page(
      "Devices",
      devices.length
        ? `${devices.length} connected`
        : "Smart home control",
      body
    );

    document.querySelectorAll(
      "[data-v126-a42-device]"
    ).forEach(button=>{
      button.addEventListener(
        "click",
        async()=>{
          const id=button.dataset.v126A42Device;

          if(!id) return;

          const original=button.textContent;

          button.disabled=true;
          button.textContent="Working…";

          try{
            await nb126Fetch(
              "/api/devices/"+
              encodeURIComponent(id)+
              "/toggle",
              {
                method:"POST",
                headers:{
                  "Content-Type":"application/json"
                },
                body:"{}"
              }
            );

            await openV126DevicesA42();

          }catch(error){
            console.error(
              "V126_DEVICE_CONTROL_ERROR",
              error
            );

            button.disabled=false;
            button.textContent=original;

            alert(
              "Device control unavailable: "+
              v126A42FriendlyError(error)
            );
          }
        }
      );
    });

    return true;

  }catch(error){
    nb126Page(
      "Devices",
      "Smart home control",
      v126A42Error(
        "Devices unavailable",
        error,
        "devices"
      )
    );

    return false;
  }
}


/* ---------------------------------------------------------
   ADD DEVICE
   --------------------------------------------------------- */

function openV126AddDeviceA42(){
  nb126Page(
    "Add Device",
    "Connect a real NoorBrain device",
    `
      <div class="nb126-form-card">

        <div class="nb126-field">
          <label for="v126A42DeviceName">
            Device name
          </label>

          <input
            class="nb126-input"
            id="v126A42DeviceName"
            autocomplete="off"
            placeholder="Living Room Light"
          >
        </div>

        <div class="nb126-field">
          <label for="v126A42DeviceType">
            Device type
          </label>

          <input
            class="nb126-input"
            id="v126A42DeviceType"
            autocomplete="off"
            placeholder="light"
          >
        </div>

        <div class="nb126-field">
          <label for="v126A42DeviceRoom">
            Room
          </label>

          <input
            class="nb126-input"
            id="v126A42DeviceRoom"
            autocomplete="off"
            placeholder="Living Room"
          >
        </div>

        <div
          id="v126A42DeviceMessage"
          class="nb126-form-message"
          hidden
        ></div>

        <button
          type="button"
          id="v126A42CreateDevice"
          class="nb126-button nb126-button-primary nb126-full"
        >
          Add Device
        </button>

        <p class="nb126-helper">
          NoorBrain will only show devices accepted by the real
          device backend. No simulated device will be created.
        </p>

      </div>
    `
  );

  const submit=document.getElementById(
    "v126A42CreateDevice"
  );

  const message=document.getElementById(
    "v126A42DeviceMessage"
  );

  submit?.addEventListener(
    "click",
    async()=>{
      const name=document.getElementById(
        "v126A42DeviceName"
      )?.value.trim();

      const type=document.getElementById(
        "v126A42DeviceType"
      )?.value.trim();

      const room=document.getElementById(
        "v126A42DeviceRoom"
      )?.value.trim();

      message.hidden=false;

      if(!name){
        message.className=
          "nb126-form-message nb126-form-message-error";

        message.textContent=
          "Enter a device name.";

        return;
      }

      submit.disabled=true;
      submit.textContent="Adding…";

      message.className=
        "nb126-form-message";

      message.textContent=
        "Connecting device…";

      try{
        await nb126Fetch(
          "/api/devices",
          {
            method:"POST",
            headers:{
              "Content-Type":"application/json"
            },
            body:JSON.stringify({
              name,
              type:type||"device",
              room:room||"Home"
            })
          }
        );

        message.className=
          "nb126-form-message nb126-form-message-success";

        message.textContent=
          "Device added.";

        setTimeout(
          ()=>openV126DevicesA42(),
          350
        );

      }catch(error){
        submit.disabled=false;
        submit.textContent="Add Device";

        message.className=
          "nb126-form-message nb126-form-message-error";

        message.textContent=
          v126A42FriendlyError(error);
      }
    }
  );

  return true;
}


/* ---------------------------------------------------------
   SMART AUTOMATION RULES
   --------------------------------------------------------- */

async function openV126AutomationRulesA42(){
  nb126Loading(
    "Smart Rules",
    "Automation that responds to your home"
  );

  try{
    const payload=await nb126Fetch(
      "/api/smart-automation/rules"
    );

    const rules=v126A42Array(
      payload,
      "rules"
    );

    const body=rules.length
      ? `
        <div class="nb126-section">

          <div class="nb126-section-title">
            <div>
              <small>AUTOMATION</small>
              <h2>Smart Rules</h2>
            </div>

            <span class="nb126-badge">
              ${rules.length}
            </span>
          </div>

          <div class="nb126-list">

            ${rules.map(rule=>{
              const trigger=
                rule.trigger ||
                rule.trigger_type ||
                "Configured trigger";

              return `
                <div class="nb126-list-row">

                  <div class="nb126-list-main">
                    <small>AUTOMATION RULE</small>

                    <h3>
                      ${esc(
                        rule.name ||
                        "Unnamed Rule"
                      )}
                    </h3>

                    <p>${esc(trigger)}</p>
                  </div>

                  ${v126A42Status(
                    rule.enabled
                  )}

                </div>
              `;
            }).join("")}

          </div>

        </div>
      `
      : v126A42Empty(
          "No smart rules yet",
          "The automation engine is ready. Create rules when real devices and triggers are available."
        );

    nb126Page(
      "Smart Rules",
      rules.length
        ? `${rules.length} configured`
        : "Automation engine ready",
      body
    );

    return true;

  }catch(error){
    nb126Page(
      "Smart Rules",
      "Automation engine",
      v126A42Error(
        "Smart Rules unavailable",
        error,
        "smart-rules"
      )
    );

    return false;
  }
}


/* ---------------------------------------------------------
   SCENES
   --------------------------------------------------------- */

async function openV126ScenesA42(){
  nb126Loading(
    "Scenes",
    "Control multiple devices together"
  );

  try{
    const payload=await nb126Fetch(
      "/api/automation/scenes"
    );

    const scenes=v126A42Array(
      payload,
      "scenes"
    );

    const body=scenes.length
      ? `
        <div class="nb126-list">

          ${scenes.map(scene=>`
            <div class="nb126-list-row">

              <div class="nb126-list-main">
                <small>SCENE</small>

                <h3>
                  ${esc(
                    scene.name ||
                    "Unnamed Scene"
                  )}
                </h3>

                <p>
                  ${
                    Array.isArray(scene.actions)
                    ? scene.actions.length+
                      " action"+
                      (scene.actions.length===1?"":"s")
                    : "Ready"
                  }
                </p>
              </div>

              ${
                scene.id
                ? `
                  <button
                    type="button"
                    class="nb126-button nb126-button-primary"
                    data-v126-a42-scene="${esc(scene.id)}"
                  >
                    Run
                  </button>
                `
                : ""
              }

            </div>
          `).join("")}

        </div>
      `
      : v126A42Empty(
          "No scenes yet",
          "Scenes let NoorBrain run several real device actions together."
        );

    nb126Page(
      "Scenes",
      scenes.length
        ? `${scenes.length} available`
        : "Whole-home actions",
      body
    );

    document.querySelectorAll(
      "[data-v126-a42-scene]"
    ).forEach(button=>{
      button.addEventListener(
        "click",
        async()=>{
          const id=button.dataset.v126A42Scene;
          const original=button.textContent;

          button.disabled=true;
          button.textContent="Running…";

          try{
            await nb126Fetch(
              "/api/automation/scenes/"+
              encodeURIComponent(id)+
              "/execute",
              {method:"POST"}
            );

            button.textContent="Done";

            setTimeout(()=>{
              button.disabled=false;
              button.textContent=original;
            },1000);

          }catch(error){
            console.error(
              "V126_SCENE_ERROR",
              error
            );

            button.disabled=false;
            button.textContent=original;

            alert(
              "Scene could not run: "+
              v126A42FriendlyError(error)
            );
          }
        }
      );
    });

    return true;

  }catch(error){
    nb126Page(
      "Scenes",
      "Whole-home actions",
      v126A42Error(
        "Scenes unavailable",
        error,
        "scenes"
      )
    );

    return false;
  }
}


/* ---------------------------------------------------------
   ROUTINES
   --------------------------------------------------------- */

async function openV126RoutinesA42(){
  nb126Loading(
    "Routines",
    "Repeatable NoorBrain actions"
  );

  try{
    const payload=await nb126Fetch(
      "/api/automation/routines"
    );

    const routines=v126A42Array(
      payload,
      "routines"
    );

    const body=routines.length
      ? `
        <div class="nb126-list">

          ${routines.map(routine=>`
            <div class="nb126-list-row">

              <div class="nb126-list-main">
                <small>ROUTINE</small>

                <h3>
                  ${esc(
                    routine.name ||
                    "Unnamed Routine"
                  )}
                </h3>

                <p>
                  ${
                    routine.schedule
                      ? esc(
                          v126A42Text(
                            routine.schedule
                          )
                        )
                      : "Ready to run"
                  }
                </p>
              </div>

              ${
                routine.id
                ? `
                  <button
                    type="button"
                    class="nb126-button nb126-button-primary"
                    data-v126-a42-routine="${esc(routine.id)}"
                  >
                    Run
                  </button>
                `
                : ""
              }

            </div>
          `).join("")}

        </div>
      `
      : v126A42Empty(
          "No routines yet",
          "Routines will appear here when configured."
        );

    nb126Page(
      "Routines",
      routines.length
        ? `${routines.length} configured`
        : "Scheduled and repeatable actions",
      body
    );

    document.querySelectorAll(
      "[data-v126-a42-routine]"
    ).forEach(button=>{
      button.addEventListener(
        "click",
        async()=>{
          const id=button.dataset.v126A42Routine;
          const original=button.textContent;

          button.disabled=true;
          button.textContent="Running…";

          try{
            await nb126Fetch(
              "/api/automation/routines/"+
              encodeURIComponent(id)+
              "/run",
              {method:"POST"}
            );

            button.textContent="Started";

            setTimeout(()=>{
              button.disabled=false;
              button.textContent=original;
            },1000);

          }catch(error){
            console.error(
              "V126_ROUTINE_ERROR",
              error
            );

            button.disabled=false;
            button.textContent=original;

            alert(
              "Routine could not run: "+
              v126A42FriendlyError(error)
            );
          }
        }
      );
    });

    return true;

  }catch(error){
    nb126Page(
      "Routines",
      "Scheduled and repeatable actions",
      v126A42Error(
        "Routines unavailable",
        error,
        "routines"
      )
    );

    return false;
  }
}


function directBridge(action){
  return V126_MODULE_BRIDGE.open(action);
}

function v126HaloStatus(message, mode=""){
  const node=document.getElementById("nb126HaloStatus");
  if(!node) return;
  node.textContent=message;
  node.dataset.voiceMode=mode;
}

function v126NativeApp(){
  return new URLSearchParams(location.search)
    .get("native_app") === "1";
}

function v126HaloSessionId(){
  const key="noorbrain.v126.halo.session";
  let id=localStorage.getItem(key);

  if(!id){
    id=(v126NativeApp() ? "android" : "web")+
      "-v126-"+Math.random().toString(36).slice(2,10);
    localStorage.setItem(key,id);
  }

  return id;
}

function v126SpeakReply(text){
  const reply=String(text||"").trim();
  if(!reply) return;

  if("speechSynthesis" in window && window.SpeechSynthesisUtterance){
    try{
      window.speechSynthesis.cancel();
      const utterance=new SpeechSynthesisUtterance(reply);
      utterance.lang="en-US";
      utterance.rate=0.95;
      window.speechSynthesis.speak(utterance);
    }catch(error){
      console.warn("V126_HALO_TTS_ERROR",error);
    }
  }
}

async function sendV126Halo(message){
  if(v126HaloBusy) return false;

  const input=document.getElementById("nb126HaloInput");
  const text=String(message ?? input?.value ?? "").trim();

  if(!text){
    v126HaloStatus("Enter a question for Noor.","error");
    return false;
  }

  if(input) input.value=text;
  v126HaloBusy=true;
  v126HaloStatus("Thinking…","thinking");

  try{
    const result=await nb126Fetch(
      "/api/halo-conversation/chat",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          text,
          session_id:v126HaloSessionId(),
          confirm:false
        })
      }
    );

    const reply=String(
      result.reply || result.message || "Noor completed the request."
    );

    v126HaloStatus(reply,"done");
    v126SpeakReply(reply);
    return result;
  }catch(error){
    v126HaloStatus(error.message || "Noor request failed.","error");
    throw error;
  }finally{
    v126HaloBusy=false;
  }
}

function shell(){
  if($("noorbrainMobile126")) return;

  const root=document.createElement("div");
  root.id="noorbrainMobile126";

  root.innerHTML=`
    <header class="nb126-topbar">
      <div class="nb126-brand">
        <span class="nb126-logo">N</span>

        <div>
          <strong>NoorBrain</strong>
          <small id="nb126Connection">Home AI</small>
        </div>
      </div>

      <button
        type="button"
        class="nb126-top-action"
        data-nb126-action="notifications"
        aria-label="Notifications"
      >
        ♢
      </button>
    </header>

    <main id="nb126Content"></main>

    <nav
      class="nb126-bottom"
      aria-label="Main navigation"
    >
      ${Object.entries(TABS).map(([id,item])=>`
        <button
          type="button"
          data-nb126-route="${id}"
          class="${id==="home" ? "active" : ""}"
        >
          <span>${item.icon}</span>
          <small>${item.title}</small>
        </button>
      `).join("")}
    </nav>
  `;

  document.body.appendChild(root);

  root.addEventListener("click",event=>{
    const route=event.target.closest(
      "[data-nb126-route]"
    );

    if(route){
      console.log(
        "V126_CLICK",
        "route",
        route.dataset.nb126Route
      );
    }

    if(route){
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      navigate(route.dataset.nb126Route);
      return;
    }

    const action=event.target.closest(
      "[data-nb126-action]"
    );

    if(action){
      console.log(
        "V126_CLICK",
        "action",
        action.dataset.nb126Action
      );
    }

    if(action){
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      runAction(action.dataset.nb126Action);
    }
  }, true);

  const initialMatch=location.hash.match(
    /^#nb-(home|automation|halo|islamic|more)$/
  );
  navigate(initialMatch?.[1] || "home",false);
}

function navigate(name,push=true){
  console.log(
    "V126_NAVIGATE",
    name,
    "push=" + push
  );
  if(!renderers[name]) name="home";

  const content=$("nb126Content");
  if(!content) return;

  logV126("NAVIGATE", {route: name, push});
  content.innerHTML=renderers[name]();

  document.querySelectorAll(
    "#noorbrainMobile126 [data-nb126-route]"
  ).forEach(button=>{
    button.classList.toggle(
      "active",
      button.dataset.nb126Route===name
    );
  });

  document.body.dataset.nb126Page=name;

  if(push){
    history.pushState(
      {nb126:name},
      "",
      `#nb-${name}`
    );
  }

  content.scrollTop=0;
  window.scrollTo(0,0);
  logV126("RESULT", {route: name, visible: !!document.querySelector("#nb126Content")});
}

function runAction(action){
  console.log(
    "V126_ACTION",
    action
  );
  logV126("CLICK", {action});

  if (action && TABS[action]) {
    navigate(action, true);
    return true;
  }

  if(action==="halo-live"){
    if(document.body.dataset.nb126Page!=="halo"){
      navigate("halo", true);
    }

    setTimeout(()=>{
      const mic = window.NoorBrainHaloMicFinalFix;

      if(!mic || typeof mic.toggle !== "function"){
        console.error("V126_HALO_MIC_API_UNAVAILABLE");
        v126HaloStatus(
          "Microphone controller unavailable. Reload NoorBrain and try again.",
          "error"
        );
        return;
      }

      console.log("V126_HALO_MIC_TOGGLE");

      Promise.resolve(mic.toggle(
        document.querySelector(
          ".nb126-orb[data-nb126-action='halo-live']"
        )
      )).catch(error=>{
        console.error(
          "V126_HALO_MIC_TOGGLE_FAILED",
          error
        );
      });
    },150);

    return true;
  }

  if(action==="halo-send"){
    sendV126Halo().catch(error=>{
      console.error("V126_HALO_SEND_FAILED",error);
    });
    return true;
  }

  if(action==="zones"){
    setNativeBackTarget(V126_PARENT_MAP.zones || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.zones || getNativeBackTarget());
    openV126Zones();
    return true;
  }

  if(action==="activity"){
    setNativeBackTarget(V126_PARENT_MAP.activity || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.activity || getNativeBackTarget());
    openV126Activity();
    return true;
  }

  if(action==="camera"){
    setNativeBackTarget(V126_PARENT_MAP.camera || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.camera || getNativeBackTarget());
    openV126Camera();
    return true;
  }

  if(action==="devices"){
    setNativeBackTarget(V126_PARENT_MAP.devices || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.devices || getNativeBackTarget());
    openV126Devices();
    return true;
  }

  if(action==="add-device"){
    setNativeBackTarget(V126_PARENT_MAP["add-device"] || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP["add-device"] || getNativeBackTarget());
    openV126AddDevice();
    return true;
  }

  if(
    action==="automation-center" ||
    action==="smart-rules"
  ){
    if(window.NoorAutomationCenterV12?.open){
      window.NoorAutomationCenterV12.open("smart");
      return true;
    }
    openV126AutomationRules();
    return true;
  }

  if(action==="scenes"){
    if(window.NoorAutomationCenterV12?.open){
      window.NoorAutomationCenterV12.open("scenes");
      return true;
    }
    setNativeBackTarget(V126_PARENT_MAP.scenes || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.scenes || getNativeBackTarget());
    openV126Scenes();
    return true;
  }

  if(action==="routines"){
    if(window.NoorAutomationCenterV12?.open){
      window.NoorAutomationCenterV12.open("routines");
      return true;
    }
    setNativeBackTarget(V126_PARENT_MAP.routines || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.routines || getNativeBackTarget());
    openV126Routines();
    return true;
  }

  if(action==="prayer"){
    setNativeBackTarget(V126_PARENT_MAP.prayer || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.prayer || getNativeBackTarget());
    openV126Prayer();
    return true;
  }

  if(
    action==="media" ||
    action==="dua-azkar"
  ){
    setNativeBackTarget(V126_PARENT_MAP.media || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.media || getNativeBackTarget());
    openV126Media();
    return true;
  }

  if(
    action==="islamic-rules" ||
    action==="reminders"
  ){
    if(window.NoorMobileRulesV12?.open){
      window.NoorMobileRulesV12.open();
      return true;
    }
    setNativeBackTarget(V126_PARENT_MAP["islamic-rules"] || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP["islamic-rules"] || getNativeBackTarget());
    openV126IslamicRules();
    return true;
  }

  if(action==="notifications"){
    setNativeBackTarget(V126_PARENT_MAP.notifications || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.notifications || getNativeBackTarget());
    openV126Notifications();
    return true;
  }

  if(action==="settings"){
    if(window.NoorMobileSettingsV11?.open){
      window.NoorMobileSettingsV11.open().catch(error=>{
        console.error("V126_SETTINGS_ERROR",error);
        openV126Settings();
      });
      return true;
    }
    setNativeBackTarget(V126_PARENT_MAP.settings || getNativeBackTarget());
    setActiveTab(V126_PARENT_MAP.settings || getNativeBackTarget());
    openV126Settings();
    return true;
  }

  const bridge = window.NoorBrainV126ModuleBridge || V126_MODULE_BRIDGE;
  const result = bridge.open ? bridge.open(action) : directBridge(action);
  logV126("BRIDGE", {action, bridge: "NoorBrainV126ModuleBridge.open", ok: !!result});

  if (result) {
    logV126("RESULT", {action, bridge: "NoorBrainV126ModuleBridge.open", ok: true});
    return true;
  }

  const fallback = window.NoorMobileProductRouterV12?.open?.(action);
  logV126("RESULT", {action, bridge: "NoorMobileProductRouterV12.open", ok: !!fallback, fallback});

  if (fallback) {
    return true;
  }

  window.dispatchEvent(
    new CustomEvent(
      "noorbrain:v126-action",
      {detail:{action}}
    )
  );
  logV126("RESULT", {action, bridge: "custom-event", ok: true});
  return true;
}

window.addEventListener("popstate",event=>{
  navigate(
    event.state?.nb126 || "home",
    false
  );
});

window.NoorBrainV126ModuleBridge = V126_MODULE_BRIDGE;

window.NoorBrainMobile126={
  version:VERSION,
  navigate,
  action:runAction,
  sendHalo:sendV126Halo,
  setHaloStatus:v126HaloStatus,
  mount:shell,
  bridge: V126_MODULE_BRIDGE
};

window.addEventListener(
  "noorbrain:v126-mount-request",
  ()=>{
    shell();
  }
);

if(document.readyState==="loading"){
  document.addEventListener(
    "DOMContentLoaded",
    ()=>{
      /*
       * Foundation only.
       * Do NOT mount automatically in A1.
       */
      console.log(
        "NOORBRAIN_MOBILE_V126_FOUNDATION_READY"
      );
    }
  );
}else{
  console.log(
    "NOORBRAIN_MOBILE_V126_FOUNDATION_READY"
  );
}

})();
