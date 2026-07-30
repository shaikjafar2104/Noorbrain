(() => {
  "use strict";

  const API = window.location.origin;
  let timer = null;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function request(path) {
    const response = await fetch(API + path, { cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
    return response.json();
  }

  function addStyles() {
    if (document.getElementById("personCardsStyles")) return;

    const style = document.createElement("style");
    style.id = "personCardsStyles";
    style.textContent = `
      .people-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
      .people-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:16px}
      .person-card{background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:14px;min-height:215px}
      .person-card-top{display:flex;align-items:center;gap:12px}
      .person-avatar{width:54px;height:54px;border-radius:50%;display:grid;place-items:center;background:#25303c;border:1px solid #354354;font-size:22px;font-weight:800;overflow:hidden;flex:0 0 54px}
      .person-avatar img{width:100%;height:100%;object-fit:cover}
      .person-name{font-size:17px;font-weight:800;margin:0 0 4px}
      .person-subtitle{color:var(--muted);font-size:12px}
      .person-presence{margin-left:auto;width:10px;height:10px;border-radius:50%;background:var(--red);box-shadow:0 0 10px rgba(255,101,119,.35)}
      .person-presence.online{background:var(--green);box-shadow:0 0 12px rgba(34,211,160,.6)}
      .person-details{display:grid;grid-template-columns:1fr 1fr;gap:10px}
      .person-detail{background:rgba(0,0,0,.16);border:1px solid rgba(255,255,255,.055);border-radius:10px;padding:10px}
      .person-detail span{display:block;color:var(--muted);font-size:11px;margin-bottom:4px}
      .person-detail strong{font-size:13px;word-break:break-word}
      .person-confidence{height:7px;border-radius:999px;background:#0d1117;overflow:hidden}
      .person-confidence span{display:block;height:100%;background:var(--green);border-radius:inherit}
      .people-empty{padding:55px 16px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:14px}
      .people-error{padding:16px;border:1px solid rgba(255,101,119,.35);background:rgba(255,101,119,.08);border-radius:12px;color:#ff9eaa}
      @media(max-width:650px){.person-details{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  function normalizeDetection(person, index, activePeople) {
    const id = person.person_id ?? person.track_id ?? person.id ?? index + 1;
    const identity = person.identity || person.name || person.recognized_name || person.label || `Person ${id}`;
    const recognized = Boolean(person.identity || person.name || person.recognized_name) && identity.toLowerCase() !== "person";
    const confidence = Number(person.identity_confidence ?? person.recognition_confidence ?? person.confidence ?? 0);
    const active = activePeople.find(item => String(item.person_id ?? item.id) === String(id));

    return {
      id,
      name: recognized ? identity : `Person ${id}`,
      recognized,
      zone: person.zone || active?.zone || "Unknown",
      confidence: Math.max(0, Math.min(1, confidence)),
      lastSeen: person.last_seen || active?.last_seen || Date.now() / 1000,
      duration: active?.duration ?? person.duration ?? 0,
      image: person.face_url || person.thumbnail_url || person.image_url || null,
      present: true
    };
  }

  function formatDuration(seconds) {
    const value = Math.max(0, Math.floor(Number(seconds) || 0));
    if (value < 60) return `${value}s`;
    const minutes = Math.floor(value / 60);
    if (minutes < 60) return `${minutes}m ${value % 60}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  }

  function render(people) {
    const grid = document.getElementById("personCardsGrid");
    const badge = document.getElementById("peopleBadge");
    if (!grid) return;

    if (badge) badge.textContent = `${people.length} active`;

    if (!people.length) {
      grid.innerHTML = `<div class="people-empty">No person is currently detected.</div>`;
      return;
    }

    grid.innerHTML = people.map(person => {
      const confidencePercent = Math.round(person.confidence * 100);
      const avatar = person.image
        ? `<img src="${escapeHtml(person.image)}" alt="${escapeHtml(person.name)}">`
        : escapeHtml(String(person.name).charAt(0).toUpperCase());

      return `
        <article class="person-card">
          <div class="person-card-top">
            <div class="person-avatar">${avatar}</div>
            <div>
              <div class="person-name">${escapeHtml(person.name)}</div>
              <div class="person-subtitle">${person.recognized ? "Recognized identity" : "Live tracked person"}</div>
            </div>
            <span class="person-presence online" title="Present"></span>
          </div>

          <div class="person-details">
            <div class="person-detail"><span>Person ID</span><strong>${escapeHtml(person.id)}</strong></div>
            <div class="person-detail"><span>Current zone</span><strong>${escapeHtml(person.zone)}</strong></div>
            <div class="person-detail"><span>Present for</span><strong>${escapeHtml(formatDuration(person.duration))}</strong></div>
            <div class="person-detail"><span>Last seen</span><strong>${new Date(Number(person.lastSeen) * 1000).toLocaleTimeString()}</strong></div>
          </div>

          <div>
            <div class="person-subtitle" style="margin-bottom:7px">Confidence ${confidencePercent}%</div>
            <div class="person-confidence"><span style="width:${confidencePercent}%"></span></div>
          </div>
        </article>
      `;
    }).join("");
  }

  async function load() {
    const grid = document.getElementById("personCardsGrid");
    try {
      const [detections, health] = await Promise.all([
        request("/detections"),
        request("/health").catch(() => ({}))
      ]);

      const rawPeople = Array.isArray(detections.people) ? detections.people : [];
      const activePeople = health?.vision?.activity_engine?.active_people || [];
      render(rawPeople.map((person, index) => normalizeDetection(person, index, activePeople)));
    } catch (error) {
      if (grid) grid.innerHTML = `<div class="people-error">Could not load people: ${escapeHtml(error.message)}</div>`;
      console.error("Person cards load failed:", error);
    }
  }

  function buildPage() {
    addStyles();

    const section = document.getElementById("page-people");
    if (!section) return;

    section.innerHTML = `
      <article class="card">
        <div class="card-head">
          <div>
            <h2>Person Cards</h2>
            <p>Live identity, presence, zone and confidence</p>
          </div>
          <div class="people-toolbar">
            <span id="peopleBadge" class="badge">0 active</span>
            <button id="personCardsRefresh" class="button secondary">Refresh</button>
          </div>
        </div>
        <div id="personCardsGrid" class="people-grid">
          <div class="people-empty">Loading people…</div>
        </div>
      </article>
    `;

    document.getElementById("personCardsRefresh")?.addEventListener("click", load);

    window.addEventListener("noor:page-opened", event => {
      if (event.detail?.page === "people") load();
    });

    load();
    timer = window.setInterval(load, 2000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildPage);
  } else {
    buildPage();
  }

  window.NoorPersonCards = {
    refresh: load,
    stop() {
      if (timer) window.clearInterval(timer);
      timer = null;
    }
  };
})();
