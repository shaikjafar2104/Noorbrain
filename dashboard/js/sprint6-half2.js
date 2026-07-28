(() => {
  "use strict";
  const api = window.NoorAPI.request;
  const router = window.NoorRouter;
  const escapeHtml = window.NoorUI.escapeHtml;
  const $ = id => document.getElementById(id);
  const state = { people: [], events: [], galleryQuery: "", galleryFilter: "all", timelineQuery: "", timelineType: "all", timelineHours: "all", timer: null };

  const num = v => Number(v || 0);
  const eventTime = e => num(e.timestamp ?? e.time);
  const eventType = e => String(e.type || e.event || "activity");
  const eventPerson = e => String(e.person_id ?? e.track_id ?? e.id ?? "");
  const personId = (p, i) => String(p.person_id ?? p.track_id ?? p.id ?? i + 1);
  const personName = (p, i) => String(p.name || p.identity_name || p.label || `Person ${personId(p, i)}`);
  const confidence = p => { const n = num(p.identity_confidence ?? p.recognition_confidence ?? p.confidence); return Math.max(0, Math.min(100, n <= 1 ? n * 100 : n)); };
  const initials = name => String(name).trim().split(/\s+/).slice(0, 2).map(x => x[0]).join("").toUpperCase() || "P";
  const fmt = ts => ts ? new Date(ts * 1000).toLocaleString() : "Never";
  const safe = value => escapeHtml(String(value ?? ""));

  async function load() {
    const [d, e] = await Promise.allSettled([api("/detections"), api("/events?limit=500")]);
    state.people = d.status === "fulfilled" && Array.isArray(d.value.people) ? d.value.people : [];
    state.events = e.status === "fulfilled" && Array.isArray(e.value.events) ? e.value.events : [];
    populateTypes(); renderGallery(); renderTimeline(); renderInsights();
  }

  function profiles() {
    const live = state.people.map((p, i) => ({ id: personId(p, i), name: personName(p, i), present: true, zone: p.zone || p.current_zone || "Unknown", confidence: confidence(p), lastSeen: Date.now() / 1000, events: 0 }));
    const map = new Map(live.map(p => [p.id, p]));
    state.events.slice().sort((a,b)=>eventTime(b)-eventTime(a)).forEach(e => {
      const id = eventPerson(e); if (!id) return;
      if (!map.has(id)) map.set(id, { id, name: e.name || e.identity_name || `Person ${id}`, present: false, zone: e.zone || e.current_zone || "Unknown", confidence: num(e.identity_confidence ?? e.confidence), lastSeen: eventTime(e), events: 0 });
      const p = map.get(id); p.events += 1; if (!p.present && eventTime(e) > p.lastSeen) { p.lastSeen = eventTime(e); p.zone = e.zone || p.zone; }
    });
    return [...map.values()].sort((a,b)=>Number(b.present)-Number(a.present)||b.lastSeen-a.lastSeen);
  }

  function renderGallery() {
    let data = profiles(); const q = state.galleryQuery.toLowerCase();
    data = data.filter(p => (state.galleryFilter === "all" || (state.galleryFilter === "present" && p.present) || (state.galleryFilter === "away" && !p.present)) && (!q || `${p.name} ${p.id} ${p.zone}`.toLowerCase().includes(q)));
    const all = profiles(), recognized = all.filter(p=>p.confidence>0).length;
    if ($("s6h2GalleryStats")) $("s6h2GalleryStats").innerHTML = `<article class="card metric"><span>Profiles</span><strong>${all.length}</strong><small>Live and historical</small></article><article class="card metric"><span>Present</span><strong>${all.filter(p=>p.present).length}</strong><small>Detected now</small></article><article class="card metric"><span>Recognized</span><strong>${recognized}</strong><small>With confidence data</small></article><article class="card metric"><span>Gallery events</span><strong>${state.events.length}</strong><small>Loaded history</small></article>`;
    const box = $("s6h2Gallery"); if (!box) return;
    box.innerHTML = data.length ? data.map(p => `<article class="card s6h2-face-card" data-s6h2-profile="${safe(p.id)}"><div class="s6h2-face-image"><div class="s6h2-face-avatar">${safe(initials(p.name))}</div><span class="s6-status ${p.present?'present':''} s6h2-face-live">${p.present?'Live':'Away'}</span></div><div class="s6h2-face-body"><div class="s6h2-face-title"><h3>${safe(p.name)}</h3><span class="badge">#${safe(p.id)}</span></div><div class="s6h2-face-meta"><div><small>Zone</small><strong>${safe(p.zone)}</strong></div><div><small>Confidence</small><strong>${Math.round(p.confidence)}%</strong></div><div><small>Last seen</small><strong>${p.present?'Now':safe(fmt(p.lastSeen))}</strong></div><div><small>Events</small><strong>${p.events}</strong></div></div></div></article>`).join("") : '<article class="card s6h2-empty">No matching profiles.</article>';
  }

  function filteredEvents() {
    const q = state.timelineQuery.toLowerCase(), now = Date.now()/1000, hours = state.timelineHours === "all" ? 0 : num(state.timelineHours);
    return state.events.filter(e => {
      const type = eventType(e); const hay = `${e.message||""} ${type} ${eventPerson(e)} ${e.zone||""} ${e.name||""}`.toLowerCase();
      return (state.timelineType === "all" || type === state.timelineType) && (!hours || eventTime(e) >= now-hours*3600) && (!q || hay.includes(q));
    }).sort((a,b)=>eventTime(b)-eventTime(a));
  }

  function populateTypes() {
    const select = $("s6h2TimelineType"); if (!select) return;
    const current = state.timelineType; const types = [...new Set(state.events.map(eventType))].sort();
    select.innerHTML = '<option value="all">All event types</option>' + types.map(t=>`<option value="${safe(t)}">${safe(t)}</option>`).join(""); select.value = current;
  }

  function renderTimeline() {
    const rows = filteredEvents(); const people = new Set(rows.map(eventPerson).filter(Boolean)); const zones = new Set(rows.map(e=>e.zone).filter(Boolean));
    if ($("s6h2TimelineSummary")) $("s6h2TimelineSummary").innerHTML = `<article class="card metric"><span>Filtered events</span><strong>${rows.length}</strong><small>Current view</small></article><article class="card metric"><span>People</span><strong>${people.size}</strong><small>Unique IDs</small></article><article class="card metric"><span>Zones</span><strong>${zones.size}</strong><small>Active locations</small></article><article class="card metric"><span>Latest event</span><strong>${rows.length?safe(eventType(rows[0])):'—'}</strong><small>${rows.length?safe(fmt(eventTime(rows[0]))):'No activity'}</small></article>`;
    if ($("s6h2TimelineCount")) $("s6h2TimelineCount").textContent = `${rows.length} events`;
    const box = $("timelineList"); if (!box) return;
    box.classList.toggle("empty", !rows.length);
    box.innerHTML = rows.length ? rows.map(e=>{const t=eventType(e);return `<div class="s6h2-timeline-item"><span class="s6h2-timeline-dot ${safe(t)}"></span><div class="s6h2-timeline-main"><strong>${safe(e.message || t)}</strong><span>Person ${safe(eventPerson(e)||'—')} · ${safe(e.zone||'No zone')} · ${safe(t)}</span></div><time class="s6h2-timeline-time">${safe(fmt(eventTime(e)))}</time></div>`}).join("") : "No matching events.";
  }

  function renderInsights() {
    const events = state.events, types = new Map(), zones = new Map(), people = new Map();
    events.forEach(e=>{const t=eventType(e),z=e.zone||"Unassigned",p=eventPerson(e)||"Unknown";types.set(t,(types.get(t)||0)+1);zones.set(z,(zones.get(z)||0)+1);people.set(p,(people.get(p)||0)+1);});
    const top = m => [...m.entries()].sort((a,b)=>b[1]-a[1])[0] || ["None",0]; const [topType,typeCount]=top(types),[topZone,zoneCount]=top(zones),[topPerson,personCount]=top(people);
    const avgConf = state.people.length ? state.people.reduce((s,p)=>s+confidence(p),0)/state.people.length : 0;
    if ($("s6h2InsightMetrics")) $("s6h2InsightMetrics").innerHTML = `<article class="card metric"><span>Events analyzed</span><strong>${events.length}</strong><small>Recent history</small></article><article class="card metric"><span>Top zone</span><strong>${safe(topZone)}</strong><small>${zoneCount} events</small></article><article class="card metric"><span>Top event</span><strong>${safe(topType)}</strong><small>${typeCount} occurrences</small></article><article class="card metric s6h2-release"><span>Sprint 6</span><strong>RC</strong><small>Half 2 installed</small></article>`;
    const insights = [
      ["📍","Most active zone", topZone === "None" ? "No zone activity is available yet." : `${topZone} generated the most activity with ${zoneCount} events.`],
      ["👤","Most active person", topPerson === "None" ? "No person history is available yet." : `Person ${topPerson} appears most often in the loaded history with ${personCount} events.`],
      ["🔔","Dominant behavior", topType === "None" ? "No event pattern is available yet." : `${topType} is the most frequent event type (${typeCount} occurrences).`],
      ["🎯","Recognition quality", state.people.length ? `Average live recognition confidence is ${Math.round(avgConf)}%.` : "No live people are currently available for confidence analysis."]
    ];
    if ($("s6h2Insights")) $("s6h2Insights").innerHTML = insights.map(x=>`<div class="s6h2-insight"><div class="s6h2-insight-icon">${x[0]}</div><h3>${safe(x[1])}</h3><p>${safe(x[2])}</p></div>`).join("");
    const rec = profiles().filter(p=>p.confidence>0).sort((a,b)=>b.confidence-a.confidence).slice(0,10);
    if ($("s6h2RecognitionStats")) $("s6h2RecognitionStats").innerHTML = rec.length ? rec.map(p=>`<div class="s6h2-rec-row"><span>${safe(p.name)}</span><div class="s6h2-rec-track"><div class="s6h2-rec-fill" style="width:${p.confidence}%"></div></div><strong>${Math.round(p.confidence)}%</strong></div>`).join("") : '<div class="muted">Recognition confidence will appear when identity data is available.</div>';
  }

  function exportTimeline() {
    const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), events: filteredEvents() }, null, 2)], {type:"application/json"});
    const url = URL.createObjectURL(blob), a = document.createElement("a"); a.href=url; a.download=`noorbrain-events-${new Date().toISOString().slice(0,10)}.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }

  router.register("gallery", {title:"Face Gallery",subtitle:"Profiles, presence and recognition",onOpen:()=>{load();state.timer=setInterval(load,4000)},onClose:()=>{clearInterval(state.timer);state.timer=null}});
  router.register("insights", {title:"AI Insights",subtitle:"Behavior patterns and recognition statistics",onOpen:load});
  router.register("timeline", {title:"Timeline 2.0",subtitle:"Search, filter and export NoorBrain events",onOpen:load});
  $("s6h2GallerySearch")?.addEventListener("input",e=>{state.galleryQuery=e.target.value;renderGallery()});
  $("s6h2GalleryFilter")?.addEventListener("change",e=>{state.galleryFilter=e.target.value;renderGallery()});
  $("s6h2GalleryRefresh")?.addEventListener("click",load);
  $("s6h2TimelineSearch")?.addEventListener("input",e=>{state.timelineQuery=e.target.value;renderTimeline()});
  $("s6h2TimelineType")?.addEventListener("change",e=>{state.timelineType=e.target.value;renderTimeline()});
  $("s6h2TimelineRange")?.addEventListener("change",e=>{state.timelineHours=e.target.value;renderTimeline()});
  $("s6h2TimelineExport")?.addEventListener("click",exportTimeline);
  $("timelineRefresh")?.addEventListener("click",load);
  $("s6h2InsightsRefresh")?.addEventListener("click",load);
})();
