(() => {
  "use strict";

  const request = window.NoorAPI && window.NoorAPI.request;
  const escapeHtml = window.NoorUI && window.NoorUI.escapeHtml
    ? window.NoorUI.escapeHtml
    : value => String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

  const firstValue = (object, keys, fallback = null) => {
    for (const key of keys) {
      if (object && object[key] !== undefined && object[key] !== null && object[key] !== "") {
        return object[key];
      }
    }
    return fallback;
  };

  const formatConfidence = value => {
    let number = Number(value || 0);
    if (number <= 1) number *= 100;
    return Math.max(0, Math.min(100, Math.round(number)));
  };

  const initials = person => {
    const name = String(firstValue(person, ["name", "person_name", "label"], "Person")).trim();
    const parts = name.split(/\s+/).filter(Boolean);
    return (parts.slice(0, 2).map(part => part[0]).join("") || "P").toUpperCase();
  };

  const cardHtml = (person, index) => {
    const id = firstValue(person, ["person_id", "track_id", "id"], index + 1);
    const name = firstValue(person, ["name", "person_name", "identity", "label"], `Person ${id}`);
    const zone = firstValue(person, ["zone", "current_zone"], "Unknown");
    const confidence = formatConfidence(firstValue(person, ["recognition_confidence", "identity_confidence", "confidence"], 0));
    const lastSeen = firstValue(person, ["last_seen_text", "last_seen", "time_text"], "Now");

    return `
      <article class="person-card" data-person-id="${escapeHtml(id)}">
        <div class="person-card-head">
          <div class="person-avatar">${escapeHtml(initials(person))}</div>
          <div class="person-title">
            <strong>${escapeHtml(name)}</strong>
            <small>ID ${escapeHtml(id)}</small>
          </div>
          <span class="presence-pill">Present</span>
        </div>
        <div class="person-meta">
          <div><span>Zone</span><strong>${escapeHtml(zone)}</strong></div>
          <div><span>Last seen</span><strong>${escapeHtml(lastSeen)}</strong></div>
          <div style="grid-column:1/-1">
            <span>Confidence</span>
            <strong>${confidence}%</strong>
            <div class="confidence-bar"><span style="width:${confidence}%"></span></div>
          </div>
        </div>
      </article>
    `;
  };

  async function refreshPersonCards() {
    const container = document.getElementById("personCards");
    const badge = document.getElementById("personCardsBadge");
    if (!container || !request) return;

    try {
      const data = await request("/detections");
      const people = Array.isArray(data.people) ? data.people : [];

      if (badge) badge.textContent = `${people.length} active`;

      if (!people.length) {
        container.className = "person-cards empty";
        container.textContent = "No people detected.";
        return;
      }

      container.className = "person-cards";
      container.innerHTML = people.map(cardHtml).join("");
    } catch (error) {
      console.error("Person cards refresh failed:", error);
      if (badge) badge.textContent = "Unavailable";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    refreshPersonCards();
    window.setInterval(refreshPersonCards, 1500);
  });

  window.NoorPersonCards = { refresh: refreshPersonCards };
})();
