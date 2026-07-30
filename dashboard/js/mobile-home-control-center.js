(() => {
  "use strict";
  if (window.NoorBrainMobileHomeControlCenter) return;

  const state = {
    devices: [],
    rooms: [],
    loading: false,
  };

  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      cache: "no-store",
      ...options,
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        payload.detail || payload.message || `HTTP ${response.status}`
      );
    }

    return payload;
  }

  function text(value) {
    return String(value ?? "")
      .replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char]);
  }

  function icon(type) {
    return ({
      light: "💡",
      switch: "⏻",
      speaker: "🔊",
      camera: "📷",
      thermostat: "🌡️",
      fan: "🌀",
      sensor: "◉",
    })[type] || "⌁";
  }

  function say(message) {
    const status = document.querySelector("#nbMobileHomeStatus");
    if (status) status.textContent = message;
  }

  async function loadDevices() {
    try {
      const payload = await request("/api/halo-oneclick/devices");
      state.devices = payload.devices || [];
    } catch (_) {
      state.devices = [];
    }

    renderDevices();
    renderRooms();
  }

  function renderDevices() {
    const host = document.querySelector("#nbMobileDeviceGrid");
    if (!host) return;

    if (!state.devices.length) {
      host.innerHTML = `
        <button class="nb-mobile-empty-action" id="nbMobileAddFirstDevice">
          <span>＋</span>
          <b>Add your first device</b>
          <small>Light, camera, plug, speaker or sensor</small>
        </button>
      `;

      document.querySelector("#nbMobileAddFirstDevice")
        ?.addEventListener("click", openAddDevice);

      return;
    }

    host.innerHTML = state.devices.slice(0, 8).map(device => `
      <button
        class="nb-mobile-device ${device.state === "on" ? "is-on" : ""}"
        data-device-toggle="${text(device.id)}"
      >
        <span class="nb-mobile-device-icon">${icon(device.type)}</span>
        <span class="nb-mobile-device-name">${text(device.name)}</span>
        <small>${text(device.room || "Home")}</small>
        <span class="nb-mobile-device-state">
          ${device.state === "on" ? "ON" : "OFF"}
        </span>
      </button>
    `).join("");

    host.querySelectorAll("[data-device-toggle]").forEach(button => {
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await request(
            `/api/halo-oneclick/devices/${button.dataset.deviceToggle}/toggle`,
            {
              method: "POST",
              body: "{}",
            }
          );
          await loadDevices();
        } catch (error) {
          say(error.message);
        } finally {
          button.disabled = false;
        }
      });
    });
  }

  function renderRooms() {
    const host = document.querySelector("#nbMobileRoomGrid");
    if (!host) return;

    const grouped = new Map();

    state.devices.forEach(device => {
      const room = device.room || "Home";
      const list = grouped.get(room) || [];
      list.push(device);
      grouped.set(room, list);
    });

    if (!grouped.size) {
      host.innerHTML = `
        <button class="nb-mobile-room-card" data-room="Hall">
          <span>🛋️</span>
          <b>Hall</b>
          <small>No devices yet</small>
        </button>
        <button class="nb-mobile-room-card" data-room="Bedroom">
          <span>🛏️</span>
          <b>Bedroom</b>
          <small>No devices yet</small>
        </button>
        <button class="nb-mobile-room-card" data-room="Kitchen">
          <span>🍳</span>
          <b>Kitchen</b>
          <small>No devices yet</small>
        </button>
      `;
      return;
    }

    host.innerHTML = [...grouped.entries()].map(([room, devices]) => `
      <button class="nb-mobile-room-card" data-room="${text(room)}">
        <span>🏠</span>
        <b>${text(room)}</b>
        <small>${devices.length} device${devices.length === 1 ? "" : "s"}</small>
      </button>
    `).join("");
  }

  function openAddDevice() {
    if (window.NoorBrainHaloOneClick?.openDeviceModal) {
      window.NoorBrainHaloOneClick.openDeviceModal();
      return;
    }

    const existing = document.querySelector("#nbDeviceModal");
    if (existing) {
      existing.classList.add("open");
      return;
    }

    say("Open Devices and tap Add Device.");
  }

  function sendHalo(command) {
    if (window.NoorBrainHaloOneClick?.sendCommand) {
      window.NoorBrainHaloOneClick.sendCommand(command);
      return;
    }

    const input = document.querySelector("#nbHaloInput");
    if (input) {
      input.value = command;
      input.focus();
    }

    document.querySelector("#nbHaloSend")?.click();
  }

  function action(name) {
    const actions = {
      halo: () => document.querySelector("#nbUniversalMic, #nbHaloMic")?.click(),
      devices: openAddDevice,
      camera: () => location.hash = "#vision",
      prayer: () => sendHalo("What is the next prayer?"),
      reminders: () => sendHalo("Show my reminders"),
      family: () => sendHalo("Who is at home?"),
      automation: () => sendHalo("Show my automations"),
      speak: () => sendHalo("Assalamu Alaikum"),
    };

    actions[name]?.();
  }

  function mount() {
    if (document.querySelector("#nbMobileHomeCenter")) return;

    const app = document.createElement("section");
    app.id = "nbMobileHomeCenter";
    app.className = "nb-mobile-home-center";

    app.innerHTML = `
      <header class="nb-mobile-home-header">
        <div>
          <span class="nb-mobile-greeting">Assalamu Alaikum</span>
          <h1>My NoorBrain Home</h1>
          <p id="nbMobileHomeStatus">Everything important in one place.</p>
        </div>
        <button class="nb-mobile-profile" data-action="halo">✦</button>
      </header>

      <section class="nb-mobile-hero">
        <button class="nb-mobile-halo-main" data-action="halo">
          <span class="nb-mobile-halo-orb">✦</span>
          <span>
            <b>Talk to HALO</b>
            <small>Tap and speak</small>
          </span>
        </button>

        <div class="nb-mobile-quick-grid">
          <button data-action="prayer"><span>🕌</span><b>Next Prayer</b></button>
          <button data-action="camera"><span>📷</span><b>Camera</b></button>
          <button data-action="reminders"><span>🔔</span><b>Reminders</b></button>
          <button data-action="automation"><span>⚡</span><b>Automation</b></button>
        </div>
      </section>

      <section class="nb-mobile-section">
        <div class="nb-mobile-section-head">
          <div>
            <span>MY HOME</span>
            <h2>Rooms</h2>
          </div>
          <button data-action="devices">＋ Add</button>
        </div>
        <div id="nbMobileRoomGrid" class="nb-mobile-room-grid"></div>
      </section>

      <section class="nb-mobile-section">
        <div class="nb-mobile-section-head">
          <div>
            <span>ONE TAP</span>
            <h2>Devices</h2>
          </div>
          <button id="nbMobileRefreshDevices">↻ Refresh</button>
        </div>
        <div id="nbMobileDeviceGrid" class="nb-mobile-device-grid"></div>
      </section>

      <section class="nb-mobile-section">
        <div class="nb-mobile-section-head">
          <div>
            <span>DAILY</span>
            <h2>Essentials</h2>
          </div>
        </div>

        <div class="nb-mobile-essential-grid">
          <button data-action="prayer">
            <span>🕌</span>
            <b>Prayer</b>
            <small>Times and reminders</small>
          </button>

          <button data-action="family">
            <span>👨‍👩‍👧‍👦</span>
            <b>Family</b>
            <small>Presence and updates</small>
          </button>

          <button data-action="camera">
            <span>👁️</span>
            <b>Vision</b>
            <small>Camera and zones</small>
          </button>

          <button data-action="reminders">
            <span>✅</span>
            <b>Tasks</b>
            <small>Reminders and routines</small>
          </button>
        </div>
      </section>

      <nav class="nb-mobile-home-nav">
        <button class="is-active" data-mobile-tab="home"><span>⌂</span><b>Home</b></button>
        <button data-action="devices"><span>⌁</span><b>Devices</b></button>
        <button data-action="halo"><span>✦</span><b>HALO</b></button>
        <button data-action="camera"><span>◉</span><b>Vision</b></button>
        <button data-action="automation"><span>⚙</span><b>More</b></button>
      </nav>
    `;

    const target = document.querySelector(
      ".mobile-main, main, .main, #content, body"
    );

    if (target === document.body) {
      target.prepend(app);
    } else {
      target.prepend(app);
    }

    document.querySelectorAll("[data-action]").forEach(button => {
      button.addEventListener("click", () => action(button.dataset.action));
    });

    document.querySelector("#nbMobileRefreshDevices")
      ?.addEventListener("click", loadDevices);

    document.body.classList.add("nb-mobile-home-mode");
    loadDevices();
  }

  window.NoorBrainMobileHomeControlCenter = {
    loadDevices,
    openAddDevice,
    sendHalo,
    version: "1.0.0",
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();


const NB={

gotoCamera(){document.querySelector(".nbv2-camera-section")?.scrollIntoView({behavior:"smooth"})},

gotoHalo(){document.querySelector("#nbv2Halo")?.scrollIntoView({behavior:"smooth"})},

gotoRooms(){document.querySelector(".nbv2-room-section")?.scrollIntoView({behavior:"smooth"})},

gotoDevices(){document.querySelector(".nbv2-device-section")?.scrollIntoView({behavior:"smooth"})},

gotoPrayer(){document.querySelector(".nbv2-prayer-section")?.scrollIntoView({behavior:"smooth"})},

gotoAutomation(){document.querySelector(".nbv2-automation-section")?.scrollIntoView({behavior:"smooth"})}

}



NB.refreshCamera=function(){

const img=document.querySelector("#nbv2CameraImage");

if(!img)return;

const url=img.src.split("?")[0];

img.src=url+"?t="+Date.now();

}

setInterval(NB.refreshCamera,2000);



NB.refreshAll=function(){

NB.refreshCamera()

location.hash=""

}



NB.quickHalo=function(){

NB.gotoHalo()

const t=document.querySelector("#nbv2HaloInput")

if(t)t.focus()

}




NB.reloadCamera=function(){

const img=document.querySelector("#nbv2CameraImage");

if(!img)return;

const u=img.src.split("?")[0];

img.src=u+"?v="+Date.now();

}




NB.cameraHealth=function(){

fetch("/api/mobile-v3/camera")

.then(r=>r.json())

.then(j=>{

const e=document.querySelector("#nb-camera-online");

if(e){

e.innerHTML=j.cameras[0].online?"ONLINE":"OFFLINE";

}

})

}

setInterval(NB.cameraHealth,5000);




window.addEventListener("load",()=>{

NB.reloadCamera();

NB.cameraHealth();

});



NB.openRoom=function(name){

console.log("Room:",name)

}

document.addEventListener("click",(e)=>{

if(e.target.classList.contains("nb-room"))

NB.openRoom(e.target.innerText)

})



NB.roomStatus=function(){

fetch("/api/mobile-v3/rooms")

.then(r=>r.json())

.then(console.log)

}



window.addEventListener("load",()=>{

NB.roomStatus()

})



NB.toggleDevice=function(id){

fetch("/api/mobile-v3/devices")

.then(r=>r.json())

.then(()=>{

console.log("toggle",id)

})

}

document.addEventListener("click",(e)=>{

if(e.target.dataset.device)

NB.toggleDevice(e.target.dataset.device)

})



NB.deviceHealth=function(){

fetch("/api/mobile-v3/devices")

.then(r=>r.json())

.then(console.log)

}



window.addEventListener("load",()=>{

NB.deviceHealth()

})



window.NB=window.NB||{};

NB.refreshCamera=function(){

const img=document.getElementById("nbQuickCamera");

if(!img)return;

img.src="/video_feed?t="+Date.now();

};

NB.cameraFullscreen=function(){

const img=document.getElementById("nbQuickCamera");

if(img&&img.requestFullscreen){

img.requestFullscreen();

}

};

NB.openCameraStudio=function(){

window.location="/studio#vision";

};

setInterval(NB.refreshCamera,3000);



window.NoorBrainQuickRefresh=function(){
if(window.NoorBrainMobileV2?.loadDevices){
NoorBrainMobileV2.loadDevices();
}
if(window.NoorBrainMobileV2?.loadConfig){
NoorBrainMobileV2.loadConfig();
}
};



window.NoorBrainStatusRefresh=function(){

fetch("/api/mobile-v3/health")

.then(r=>r.json())

.then(()=>{

document.getElementById("camStatus").innerHTML="🟢 Camera";

document.getElementById("haloStatus").innerHTML="🟢 HALO";

document.getElementById("visionStatus").innerHTML="🟢 Vision";

document.getElementById("deviceStatus").innerHTML="🟢 Devices";

})

.catch(()=>{

document.getElementById("camStatus").innerHTML="🔴 Camera";

});

};

setInterval(NoorBrainStatusRefresh,5000);

