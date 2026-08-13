(() => {
"use strict";

if (window.__NOOR_PRODUCT_DASHBOARD_V12__) return;
window.__NOOR_PRODUCT_DASHBOARD_V12__ = true;

const mobile =
  location.pathname.includes("/mobile");

function addStyle() {
  if (document.getElementById("nbProductDashStyle"))
    return;

  const style=document.createElement("style");
  style.id="nbProductDashStyle";

  style.textContent=`
  /* ===============================
     NOORBRAIN PRODUCT DASHBOARD
     =============================== */

  .nb-product-section-title{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom:12px;
  }

  .nb-product-section-title h2{
    margin:0;
  }

  .nb-product-pill{
    border-radius:999px;
    padding:5px 10px;
    font-size:11px;
    font-weight:700;
    background:rgba(65,210,150,.12);
    color:#65e0a6;
  }

  /* ---------- DESKTOP ---------- */

  body:not(.nb-mobile-product) .dashboard-grid{
    align-items:start;
  }

  body:not(.nb-mobile-product)
  [data-page="dashboard"] .camera-card{
    min-width:0;
  }

  body:not(.nb-mobile-product)
  [data-page="dashboard"] .recent-events,
  body:not(.nb-mobile-product)
  [data-page="dashboard"] .events-card{
    max-height:605px;
    overflow:hidden;
  }

  body:not(.nb-mobile-product)
  .nb-product-compact-events{
    max-height:430px !important;
    overflow:auto !important;
  }

  body:not(.nb-mobile-product)
  .nb-product-secondary{
    margin-top:16px;
  }

  /* ---------- MOBILE ---------- */

  body.nb-mobile-product main{
    padding-bottom:105px;
  }

  body.nb-mobile-product .nbv2-hero{
    margin-bottom:12px;
  }

  body.nb-mobile-product
  #nbv2CameraSection{
    order:1;
  }

  body.nb-mobile-product
  .nbv2-status-section{
    order:2;
  }

  body.nb-mobile-product
  #nbv2Devices{
    order:3;
  }

  body.nb-mobile-product
  #nbv2Halo{
    order:4;
  }

  body.nb-mobile-product
  #nbv2Modules{
    order:5;
  }

  body.nb-mobile-product main{
    display:flex;
    flex-direction:column;
  }

  body.nb-mobile-product
  .nbv2-camera-section{
    padding:14px;
    border-radius:18px;
  }

  body.nb-mobile-product
  .nbv2-camera-hero{
    border-radius:14px;
    overflow:hidden;
  }

  body.nb-mobile-product
  .nbv2-camera-actions{
    display:grid !important;
    grid-template-columns:
      repeat(3,minmax(0,1fr));
    gap:8px;
  }

  body.nb-mobile-product
  .nbv2-camera-actions button{
    min-width:0;
    padding:10px 5px;
    font-size:11px;
  }

  body.nb-mobile-product
  #nbv2CameraRefresh{
    grid-column:auto;
  }

  body.nb-mobile-product
  #nbv2CameraOverlay{
    grid-column:span 2;
  }

  body.nb-mobile-product
  .nbv2-status-grid{
    grid-template-columns:
      repeat(2,minmax(0,1fr)) !important;
  }

  body.nb-mobile-product
  .nbv2-module-grid{
    display:none !important;
  }

  body.nb-mobile-product
  #nbv2Modules .nbv2-section-head{
    display:none !important;
  }

  body.nb-mobile-product
  #nbv2Modules{
    padding:0 !important;
    margin:0 !important;
    min-height:0 !important;
  }

  body.nb-mobile-product
  .nbv2-device-section,
  body.nb-mobile-product
  .nbv2-halo-section,
  body.nb-mobile-product
  .nbv2-status-section{
    border-radius:18px;
  }

  .nb-phone-overview{
    display:none;
  }

  body.nb-mobile-product
  .nb-phone-overview{
    display:grid;
    grid-template-columns:
      repeat(3,minmax(0,1fr));
    gap:8px;
    margin:0 0 12px;
  }

  .nb-phone-stat{
    padding:11px 8px;
    border-radius:14px;
    background:rgba(255,255,255,.055);
    border:1px solid rgba(255,255,255,.06);
    text-align:center;
  }

  .nb-phone-stat b{
    display:block;
    font-size:15px;
    margin-bottom:3px;
  }

  .nb-phone-stat small{
    opacity:.62;
    font-size:9px;
  }

  .nb-phone-activity{
    display:none;
  }

  body.nb-mobile-product
  .nb-phone-activity{
    display:block;
    margin:0 0 12px;
    padding:14px;
    border-radius:18px;
    background:rgba(255,255,255,.035);
    border:1px solid rgba(255,255,255,.06);
  }

  .nb-phone-activity-head{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:10px;
  }

  .nb-phone-activity-head b{
    font-size:14px;
  }

  .nb-phone-activity-head span{
    font-size:10px;
    opacity:.6;
  }

  .nb-phone-event{
    display:flex;
    align-items:center;
    gap:9px;
    padding:8px 0;
    border-bottom:
      1px solid rgba(255,255,255,.05);
  }

  .nb-phone-event:last-child{
    border-bottom:0;
  }

  .nb-phone-event-dot{
    width:7px;
    height:7px;
    border-radius:50%;
    background:#58dc98;
    flex:0 0 auto;
  }

  .nb-phone-event-main{
    min-width:0;
    flex:1;
  }

  .nb-phone-event-main b{
    display:block;
    font-size:11px;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
  }

  .nb-phone-event-main small{
    opacity:.55;
    font-size:9px;
  }

  @media(max-width:420px){
    body.nb-mobile-product
    .nbv2-camera-actions{
      grid-template-columns:
        repeat(2,minmax(0,1fr));
    }

    body.nb-mobile-product
    #nbv2CameraOverlay{
      grid-column:auto;
    }
  }
  `;

  document.head.appendChild(style);
}

function mobileOverview() {
  if (!mobile) return;

  document.body.classList.add(
    "nb-mobile-product"
  );

  const camera=
    document.getElementById(
      "nbv2CameraSection"
    );

  if (!camera) return;

  if (!document.getElementById(
    "nbPhoneOverview"
  )) {
    const overview=
      document.createElement("section");

    overview.id="nbPhoneOverview";
    overview.className="nb-phone-overview";

    overview.innerHTML=`
      <div class="nb-phone-stat">
        <b id="nbPhonePeople">--</b>
        <small>People</small>
      </div>

      <div class="nb-phone-stat">
        <b id="nbPhoneVision">--</b>
        <small>Vision</small>
      </div>

      <div class="nb-phone-stat">
        <b id="nbPhoneVoice">--</b>
        <small>Voice</small>
      </div>
    `;

    camera.parentNode.insertBefore(
      overview,
      camera
    );
  }

  if (!document.getElementById(
    "nbPhoneActivity"
  )) {
    const activity=
      document.createElement("section");

    activity.id="nbPhoneActivity";
    activity.className="nb-phone-activity";

    activity.innerHTML=`
      <div class="nb-phone-activity-head">
        <b>Recent Activity</b>
        <span>LIVE</span>
      </div>

      <div id="nbPhoneActivityList">
        <div class="nb-phone-event">
          <span class="nb-phone-event-dot"></span>
          <div class="nb-phone-event-main">
            <b>Waiting for activity…</b>
            <small>NoorBrain</small>
          </div>
        </div>
      </div>
    `;

    camera.insertAdjacentElement(
      "afterend",
      activity
    );
  }
}

async function json(url) {
  const controller=new AbortController();

  const timer=setTimeout(
    ()=>controller.abort(),
    4500
  );

  try {
    const response=await fetch(url,{
      cache:"no-store",
      signal:controller.signal
    });

    if (!response.ok)
      throw new Error(
        `HTTP ${response.status}`
      );

    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

function text(id,value) {
  const el=document.getElementById(id);
  if (el) el.textContent=value;
}

function extractEvents(data) {
  if (!data) return [];

  const candidates=[
    data.events,
    data.recent_events,
    data.history,
    data.activity,
    data.items
  ];

  for (const item of candidates) {
    if (Array.isArray(item))
      return item;
  }

  return [];
}

function eventLabel(event) {
  return String(
    event?.event ||
    event?.type ||
    event?.name ||
    event?.trigger ||
    "Activity"
  )
  .replaceAll("_"," ");
}

function eventTime(event) {
  const value=
    event?.time_text ||
    event?.timestamp ||
    event?.created_at ||
    event?.time;

  if (!value) return "Recently";

  if (typeof value==="string" &&
      !/^\d+(\.\d+)?$/.test(value))
    return value;

  const number=Number(value);

  if (!Number.isFinite(number))
    return "Recently";

  const ms=
    number < 100000000000
      ? number*1000
      : number;

  try {
    return new Date(ms)
      .toLocaleTimeString([],{
        hour:"numeric",
        minute:"2-digit"
      });
  } catch {
    return "Recently";
  }
}

function renderEvents(events) {
  const list=document.getElementById(
    "nbPhoneActivityList"
  );

  if (!list) return;

  if (!events.length) {
    list.innerHTML=`
      <div class="nb-phone-event">
        <span class="nb-phone-event-dot"></span>
        <div class="nb-phone-event-main">
          <b>No recent activity</b>
          <small>Monitoring live</small>
        </div>
      </div>
    `;
    return;
  }

  list.innerHTML=
    events.slice(0,4).map(event=>`
      <div class="nb-phone-event">
        <span class="nb-phone-event-dot"></span>

        <div class="nb-phone-event-main">
          <b>${escapeHtml(
            eventLabel(event)
          )}</b>

          <small>${escapeHtml(
            eventTime(event)
          )}</small>
        </div>
      </div>
    `).join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

async function refreshMobile() {
  if (!mobile) return;

  const results=await Promise.allSettled([
    json("/api/vision-intelligence/health"),
    json("/api/person-presence/health"),
    json("/api/pi-wake-v16/health"),
    json("/api/activity-intelligence/events"),
    json("/api/activity/events"),
    json("/api/person-presence/events")
  ]);

  const get=index=>
    results[index].status==="fulfilled"
      ? results[index].value
      : null;

  const vision=get(0);
  const presence=get(1);
  const voice=get(2);

  text(
    "nbPhonePeople",
    presence?.active_count ?? "0"
  );

  text(
    "nbPhoneVision",
    vision?.status==="healthy"
      ? "Live"
      : "Check"
  );

  text(
    "nbPhoneVoice",
    voice?.natural_voice_ready
      ? "Ready"
      : "Check"
  );

  let events=[];

  for (let i=3;i<=5;i++) {
    events=extractEvents(get(i));

    if (events.length)
      break;
  }

  renderEvents(events);
}

function compactDesktop() {
  if (mobile) return;

  const candidates=[
    ...document.querySelectorAll(
      '[id*="event" i], [class*="event" i]'
    )
  ];

  candidates.forEach(el=>{
    const txt=
      (el.textContent || "")
      .toLowerCase();

    if (
      txt.includes("recent") &&
      txt.includes("event")
    ) {
      el.classList.add(
        "nb-product-compact-events"
      );
    }
  });
}

function start() {
  addStyle();
  mobileOverview();
  compactDesktop();

  if (mobile) {
    refreshMobile();

    setInterval(
      refreshMobile,
      15000
    );
  }

  console.log(
    "NOOR_PRODUCT_DASHBOARD_V12_READY"
  );
}

window.NoorProductDashboardV12={
  version:"12.1.5",
  refresh:refreshMobile
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
