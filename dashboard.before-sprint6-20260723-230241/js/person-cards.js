(() => {
  "use strict";

  const API = window.NoorAPI;
  const UI = window.NoorUI;
  if (!API || !UI) return;

  const { escapeHtml, setText } = UI;
  let timer = null;

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function personId(item, fallback) {
    return item.person_id ?? item.track_id ?? item.id ?? fallback;
  }

  function confidence(item) {
    const raw = Number(item.confidence ?? item.score ?? item.identity_confidence ?? 0);
    return Math.max(0, Math.min(1, raw));
  }

  function elapsed(seconds) {
    const value = Math.max(0, Number(seconds || 0));
    if (value < 60) return `${Math.round(value)}s`;
    if (value < 3600) return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
    return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`;
  }

  function mergePeople(health, detections) {
    const vision = health?.vision || {};
    const activity = vision.activity_engine || {};
    const tracker = vision.person_tracker || {};
    const active = asArray(activity.active_people);
    const tracks = asArray(tracker.tracks);
    const detected = asArray(detections?.people);
    const map = new Map();

    const add = (item, index, source) => {
      const id = personId(item, index + 1);
      const key = String(id);
      const current = map.get(key) || { person_id: id };
      map.set(key, { ...current, ...item, source, person_id: id });
    };

    tracks.forEach((item, index) => add(item, index, "track"));
    detected.forEach((item, index) => add(item, index, "detection"));
    active.forEach((item, index) => add(item, index, "presence"));

    return [...map.values()].sort((a, b) => Number(personId(a, 0)) - Number(personId(b, 0)));
  }

  function renderCard(person) {
    const id = personId(person, "—");
    const name = person.name || person.identity_name || person.label || `Person ${id}`;
    const zone = person.zone || person.current_zone || "Unknown";
    const conf = confidence(person);
    const percent = Math.round(conf * 100);
    const duration = person.duration ?? person.present_for ?? person.age ?? 0;
    const lastSeen = person.last_seen_text || person.time_text || (person.missing ? "Recently" : "Now");
    const present = person.missing !== true && person.active !== false;
    const initial = String(name).trim().charAt(0).toUpperCase() || "P";

    return `
      <article class="person-profile-card">
        <div class="person-profile-head">
          <div class="person-avatar">${escapeHtml(initial)}</div>
          <div class="person-profile-name">
            <strong>${escapeHtml(name)}</strong>
            <small>ID ${escapeHtml(id)}</small>
          </div>
          <span class="presence-pill ${present ? "present" : "away"}">
            <span class="presence-dot"></span>${present ? "Present" : "Away"}
          </span>
        </div>
        <div class="person-profile-details">
          <div class="person-detail"><span>Zone</span><strong>${escapeHtml(zone)}</strong></div>
          <div class="person-detail"><span>Present for</span><strong>${escapeHtml(elapsed(duration))}</strong></div>
          <div class="person-detail"><span>Last seen</span><strong>${escapeHtml(lastSeen)}</strong></div>
          <div class="person-detail"><span>Confidence</span><strong>${percent}%</strong></div>
        </div>
        <div class="confidence-track"><div class="confidence-fill" style="width:${percent}%"></div></div>
      </article>`;
  }

  async function refresh() {
    const container = document.getElementById("personCards");
    if (!container) return;

    try {
      const [health, detections] = await Promise.all([
        API.request("/health"),
        API.request("/detections").catch(() => ({ people: [] }))
      ]);
      const people = mergePeople(health, detections);
      setText("personCardsBadge", `${people.length} active`);
      container.innerHTML = people.length
        ? people.map(renderCard).join("")
        : '<div class="person-empty">No active people.</div>';
    } catch (error) {
      setText("personCardsBadge", "Offline");
      container.innerHTML = '<div class="person-empty">Person data unavailable.</div>';
      console.error("Person Cards refresh failed:", error);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    refresh();
    timer = window.setInterval(refresh, 2000);
  });

  window.addEventListener("beforeunload", () => {
    if (timer) window.clearInterval(timer);
  });
})();
