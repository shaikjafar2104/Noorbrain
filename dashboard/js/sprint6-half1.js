(() => {
  "use strict";
  const api = window.NoorAPI.request;
  const router = window.NoorRouter;
  const escapeHtml = window.NoorUI.escapeHtml;
  const $ = id => document.getElementById(id);
  const store = {people: [], events: [], query: "", filter: "all", timer: null};

  function nowSeconds(){ return Date.now()/1000; }
  function personId(p,i){ return p.person_id ?? p.track_id ?? p.id ?? i+1; }
  function personName(p,i){ return p.name || p.identity_name || p.label || `Person ${personId(p,i)}`; }
  function confidence(p){ const n=Number(p.identity_confidence ?? p.recognition_confidence ?? p.confidence ?? 0); return n<=1?n*100:n; }
  function initials(name){ return String(name).split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("").toUpperCase() || "P"; }
  function eventTime(e){ return Number(e.timestamp ?? e.time ?? 0); }
  function eventPerson(e){ return String(e.person_id ?? e.track_id ?? e.id ?? ""); }
  function fmtTime(ts){ if(!ts) return "Never"; return new Date(ts*1000).toLocaleString(); }
  function duration(sec){ sec=Math.max(0,Math.round(sec||0)); if(sec<60)return `${sec}s`; if(sec<3600)return `${Math.floor(sec/60)}m ${sec%60}s`; return `${Math.floor(sec/3600)}h ${Math.floor(sec%3600/60)}m`; }

  async function fetchData(){
    const [detections, events] = await Promise.allSettled([api("/detections"),api("/events?limit=500")]);
    const d=detections.status==="fulfilled"?detections.value:{};
    const e=events.status==="fulfilled"?events.value:{};
    store.people=Array.isArray(d.people)?d.people:[];
    store.events=Array.isArray(e.events)?e.events:[];
    renderPresence(); renderAnalytics();
  }

  function enrich(p,i){
    const id=String(personId(p,i));
    const matching=store.events.filter(e=>eventPerson(e)===id).sort((a,b)=>eventTime(b)-eventTime(a));
    const latest=matching[0];
    const first=[...matching].sort((a,b)=>eventTime(a)-eventTime(b))[0];
    const present=true;
    const zone=p.zone || p.current_zone || latest?.zone || "Unknown";
    return {raw:p,id,name:personName(p,i),present,zone,confidence:confidence(p),lastSeen:eventTime(latest)||nowSeconds(),firstSeen:eventTime(first)||nowSeconds(),events:matching.length};
  }

  function cardsData(){
    const live=store.people.map(enrich);
    const liveIds=new Set(live.map(x=>x.id));
    const historical=new Map();
    store.events.forEach(e=>{
      const id=eventPerson(e); if(!id||liveIds.has(id))return;
      const old=historical.get(id);
      if(!old||eventTime(e)>old.lastSeen) historical.set(id,{id,name:e.name||e.identity_name||`Person ${id}`,present:false,zone:e.zone||"Unknown",confidence:0,lastSeen:eventTime(e),firstSeen:eventTime(e),events:1,raw:{}});
      else old.events+=1;
    });
    return [...live,...historical.values()].sort((a,b)=>Number(b.present)-Number(a.present)||b.lastSeen-a.lastSeen);
  }

  function renderPresence(){
    let data=cardsData();
    const q=store.query.toLowerCase();
    data=data.filter(p=>(store.filter==="all"||(store.filter==="present"&&p.present)||(store.filter==="away"&&!p.present))&&(!q||`${p.name} ${p.zone} ${p.id}`.toLowerCase().includes(q)));
    const all=cardsData(), present=all.filter(p=>p.present).length;
    const summary=$("s6PresenceSummary");
    if(summary) summary.innerHTML=`<article class="card metric"><span>Total profiles</span><strong>${all.length}</strong><small>Live and historical</small></article><article class="card metric"><span>Present now</span><strong>${present}</strong><small>Current detections</small></article><article class="card metric"><span>Away</span><strong>${Math.max(0,all.length-present)}</strong><small>Seen previously</small></article><article class="card metric"><span>Events loaded</span><strong>${store.events.length}</strong><small>Recent history</small></article>`;
    const box=$("s6PersonCards"); if(!box)return;
    if(!data.length){box.innerHTML='<div class="card s6-empty">No matching people.</div>';return;}
    box.innerHTML=data.map(p=>`<article class="card s6-person-card" data-s6-person="${escapeHtml(p.id)}"><div class="s6-person-head"><div class="s6-avatar">${escapeHtml(initials(p.name))}</div><div class="s6-person-title"><h3>${escapeHtml(p.name)}</h3><span class="s6-status ${p.present?'present':''}">${p.present?'Present':'Away'}</span></div></div><div class="s6-person-meta"><div><small>Zone</small><strong>${escapeHtml(p.zone)}</strong></div><div><small>Confidence</small><strong>${Math.round(p.confidence)}%</strong></div><div><small>Last seen</small><strong>${p.present?'Now':escapeHtml(fmtTime(p.lastSeen))}</strong></div><div><small>Events</small><strong>${p.events}</strong></div></div></article>`).join("");
  }

  function openDrawer(id){
    const p=cardsData().find(x=>x.id===String(id)); if(!p)return;
    const recent=store.events.filter(e=>eventPerson(e)===p.id).sort((a,b)=>eventTime(b)-eventTime(a)).slice(0,8);
    $("s6DrawerContent").innerHTML=`<div class="s6-detail-avatar">${escapeHtml(initials(p.name))}</div><h2>${escapeHtml(p.name)}</h2><span class="s6-status ${p.present?'present':''}">${p.present?'Present now':'Away'}</span><div class="s6-detail-grid"><div><small>Person ID</small><strong>${escapeHtml(p.id)}</strong></div><div><small>Current zone</small><strong>${escapeHtml(p.zone)}</strong></div><div><small>Confidence</small><strong>${Math.round(p.confidence)}%</strong></div><div><small>Presence time</small><strong>${p.present?duration(nowSeconds()-p.firstSeen):'—'}</strong></div><div><small>Last seen</small><strong>${escapeHtml(fmtTime(p.lastSeen))}</strong></div><div><small>Recent events</small><strong>${p.events}</strong></div></div><h3 style="margin-top:24px">Recent activity</h3><div class="timeline">${recent.length?recent.map(e=>`<div class="timeline-item"><strong>${escapeHtml(e.message||e.type||e.event||'Activity')}</strong><time>${escapeHtml(fmtTime(eventTime(e)))}</time></div>`).join(''):'<div class="muted">No events found.</div>'}</div>`;
    $("s6PersonDrawer").classList.add("open"); $("s6DrawerBackdrop").classList.add("open"); $("s6PersonDrawer").setAttribute("aria-hidden","false");
  }
  function closeDrawer(){ $("s6PersonDrawer")?.classList.remove("open"); $("s6DrawerBackdrop")?.classList.remove("open"); $("s6PersonDrawer")?.setAttribute("aria-hidden","true"); }

  function barRows(map){
    const rows=[...map.entries()].sort((a,b)=>b[1]-a[1]); const max=Math.max(1,...rows.map(x=>x[1]));
    return rows.length?rows.map(([name,count])=>`<div class="s6-bar-row"><span class="s6-bar-label" title="${escapeHtml(name)}">${escapeHtml(name)}</span><div class="s6-bar-track"><div class="s6-bar-fill" style="width:${Math.max(2,count/max*100)}%"></div></div><strong>${count}</strong></div>`).join(''):'<div class="muted">No activity data.</div>';
  }
  function renderAnalytics(){
    const zoneMap=new Map(), typeMap=new Map();
    store.events.forEach(e=>{const z=e.zone||e.current_zone||"Unassigned";const t=e.type||e.event||"activity";zoneMap.set(z,(zoneMap.get(z)||0)+1);typeMap.set(t,(typeMap.get(t)||0)+1);});
    const metrics=$("s6AnalyticsMetrics"); if(metrics)metrics.innerHTML=`<article class="card metric"><span>Events</span><strong>${store.events.length}</strong><small>Loaded from timeline</small></article><article class="card metric"><span>Active people</span><strong>${store.people.length}</strong><small>Live detections</small></article><article class="card metric"><span>Active zones</span><strong>${[...zoneMap.keys()].filter(x=>x!=="Unassigned").length}</strong><small>Zones with events</small></article><article class="card metric"><span>Event types</span><strong>${typeMap.size}</strong><small>Activity categories</small></article>`;
    if($("s6ZoneBars"))$("s6ZoneBars").innerHTML=barRows(zoneMap);
    if($("s6EventBars"))$("s6EventBars").innerHTML=barRows(typeMap);
  }

  router.register("presence",{title:"Live Presence",subtitle:"Person cards, status and details",onOpen:()=>{fetchData();store.timer=setInterval(fetchData,3000);},onClose:()=>{clearInterval(store.timer);store.timer=null;}});
  router.register("analytics",{title:"Zone Analytics",subtitle:"Recent activity overview",onOpen:fetchData});
  document.addEventListener("click",e=>{const card=e.target.closest("[data-s6-person]");if(card)openDrawer(card.dataset.s6Person);if(e.target.closest("#s6DrawerClose")||e.target.id==="s6DrawerBackdrop")closeDrawer();});
  $("s6PeopleSearch")?.addEventListener("input",e=>{store.query=e.target.value;renderPresence();});
  $("s6PresenceFilter")?.addEventListener("change",e=>{store.filter=e.target.value;renderPresence();});
  $("s6PresenceRefresh")?.addEventListener("click",fetchData);
})();
