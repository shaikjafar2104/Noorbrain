(() => {
  "use strict";

  const FORM_ID = "haloForm";
  const INPUT_ID = "haloInput";
  const MESSAGES_ID = "chatMessages";
  const BADGE_ID = "haloBadge";
  const AGENT_URL = "/api/offline-agent/chat";
  const HEALTH_URL = "/api/offline-agent/health";
  const SKILLS_URL = "/api/offline-agent/skills/status";
  const SESSION_KEY = "noorbrain.halo.session";

  let pendingAction = null;
  let requestInFlight = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function sessionId() {
    let value = localStorage.getItem(SESSION_KEY);
    if (!value) {
      value = `dashboard-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      localStorage.setItem(SESSION_KEY, value);
    }
    return value;
  }

  function setBadge(text, state = "ready") {
    const badge = byId(BADGE_ID);
    if (!badge) return;
    badge.textContent = text;
    badge.dataset.state = state;
  }

  function appendBubble(role, text, extraClass = "") {
    const box = byId(MESSAGES_ID);
    if (!box) return null;

    const bubble = document.createElement("div");
    bubble.className = `bubble ${role} ${extraClass}`.trim();
    bubble.textContent = String(text ?? "");
    box.appendChild(bubble);
    box.scrollTop = box.scrollHeight;
    return bubble;
  }

  function appendConfirmation(payload) {
    const box = byId(MESSAGES_ID);
    if (!box) return;

    const wrapper = document.createElement("div");
    wrapper.className = "halo-confirmation";

    const confirm = document.createElement("button");
    confirm.type = "button";
    confirm.className = "button success";
    confirm.textContent = "Confirm";

    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "button secondary";
    cancel.textContent = "Cancel";

    confirm.addEventListener("click", async () => {
      wrapper.remove();
      await sendMessage(payload.text, true);
    });

    cancel.addEventListener("click", () => {
      pendingAction = null;
      wrapper.remove();
      appendBubble("assistant", "Action cancelled.");
      setBadge("Ready");
    });

    wrapper.append(confirm, cancel);
    box.appendChild(wrapper);
    box.scrollTop = box.scrollHeight;
  }

  function ensureSkillsPanel() {
    if (byId("haloSkillsPanel")) return;

    const form = byId(FORM_ID);
    const card = form?.closest(".card");
    if (!card) return;

    const panel = document.createElement("div");
    panel.id = "haloSkillsPanel";
    panel.className = "halo-skills-panel";
    panel.innerHTML = `
      <div class="halo-skills-head">
        <strong>HALO Skills</strong>
        <button id="haloSkillsRefresh" class="text-button" type="button">Refresh</button>
      </div>
      <div id="haloSkillsList" class="halo-skills-list">
        <span class="halo-skill">Loading…</span>
      </div>
      <div class="halo-quick-actions">
        <button type="button" data-halo-prompt="Ghar ka status batao">Home status</button>
        <button type="button" data-halo-prompt="Camera status">Camera</button>
        <button type="button" data-halo-prompt="Activity summary">Activity</button>
        <button type="button" data-halo-prompt="Show automation summary">Automation</button>
      </div>
    `;

    card.insertBefore(panel, form);

    byId("haloSkillsRefresh")?.addEventListener("click", loadSkills);
    panel.querySelectorAll("[data-halo-prompt]").forEach(button => {
      button.addEventListener("click", () => {
        sendMessage(button.dataset.haloPrompt, false);
      });
    });
  }

  async function loadSkills() {
    const list = byId("haloSkillsList");
    if (!list) return;

    try {
      const response = await fetch(SKILLS_URL, {
        cache: "no-store",
        headers: { "Accept": "application/json" }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const payload = await response.json();
      const skills = Array.isArray(payload.skills) ? payload.skills : [];
      list.innerHTML = skills.map(skill => `
        <span class="halo-skill ${skill.available ? "is-ready" : "is-offline"}">
          <span class="halo-skill-dot"></span>${skill.name}
        </span>
      `).join("");
    } catch (error) {
      list.innerHTML = `<span class="halo-skill is-offline">Skills unavailable</span>`;
      console.error("HALO skill status failed:", error);
    }
  }

  async function parseResponse(response) {
    const raw = await response.text();
    try {
      return JSON.parse(raw);
    } catch {
      return {
        status: response.ok ? "ok" : "error",
        reply: raw || `HTTP ${response.status}`
      };
    }
  }

  async function sendMessage(text, confirm = false) {
    if (requestInFlight) return;

    const input = byId(INPUT_ID);
    const form = byId(FORM_ID);
    const submit = form?.querySelector('button[type="submit"]');
    const cleanText = String(text || "").trim();
    if (!cleanText) return;

    requestInFlight = true;
    if (input) input.disabled = true;
    if (submit) {
      submit.disabled = true;
      submit.dataset.originalText ||= submit.textContent;
      submit.textContent = "Thinking…";
    }

    if (!confirm) appendBubble("user", cleanText);

    const waiting = appendBubble("assistant", "HALO is thinking…", "halo-waiting");
    setBadge("Thinking…", "busy");

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 120000);

    try {
      const response = await fetch(AGENT_URL, {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          text: cleanText,
          session_id: sessionId(),
          confirm
        }),
        signal: controller.signal
      });

      const payload = await parseResponse(response);
      waiting?.remove();
      if (!response.ok) {
        throw new Error(payload.detail || payload.reply || `HTTP ${response.status}`);
      }

      appendBubble("assistant", payload.reply || payload.response || "HALO returned no reply.");

      if (payload.status === "needs_confirmation") {
        pendingAction = { text: cleanText, tool: payload.tool || null };
        appendConfirmation(pendingAction);
        setBadge("Confirm action", "confirm");
      } else if (payload.status === "error") {
        setBadge("Error", "error");
      } else {
        pendingAction = null;
        setBadge("Ready");
      }
    } catch (error) {
      waiting?.remove();
      const message = error?.name === "AbortError"
        ? "HALO took too long to respond. Please try again."
        : `HALO unavailable: ${error?.message || error}`;
      appendBubble("assistant", message);
      setBadge("Offline", "error");
      console.error("HALO dashboard request failed:", error);
    } finally {
      window.clearTimeout(timeout);
      requestInFlight = false;
      if (input) {
        input.disabled = false;
        input.focus();
      }
      if (submit) {
        submit.disabled = false;
        submit.textContent = submit.dataset.originalText || "Send";
      }
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    event.stopImmediatePropagation();

    const input = byId(INPUT_ID);
    const text = input?.value?.trim();
    if (!text) return;
    input.value = "";
    await sendMessage(text, false);
  }

  async function healthCheck() {
    try {
      const response = await fetch(HEALTH_URL, {
        cache: "no-store",
        headers: { "Accept": "application/json" }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setBadge(payload.mode === "local_fast" ? "Local Ready" : "Ready");
    } catch {
      setBadge("Offline", "error");
    }
  }

  function addStyles() {
    if (byId("haloV2Styles")) return;

    const style = document.createElement("style");
    style.id = "haloV2Styles";
    style.textContent = `
      .halo-confirmation { display:flex; gap:8px; padding:10px 0 4px; }
      .halo-waiting { opacity:.7; font-style:italic; }
      #haloBadge[data-state="busy"] { opacity:.75; }
      #haloBadge[data-state="error"] { background:rgba(239,68,68,.16); color:#fca5a5; }
      #haloBadge[data-state="confirm"] { background:rgba(245,158,11,.16); color:#fcd34d; }
      .halo-skills-panel {
        margin:12px 0 14px;
        padding:12px;
        border:1px solid rgba(255,255,255,.08);
        border-radius:12px;
        background:rgba(255,255,255,.025);
      }
      .halo-skills-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:9px; }
      .halo-skills-list { display:flex; flex-wrap:wrap; gap:7px; }
      .halo-skill {
        display:inline-flex; align-items:center; gap:6px;
        padding:5px 9px; border-radius:999px;
        background:rgba(148,163,184,.1); font-size:.75rem;
      }
      .halo-skill-dot { width:7px; height:7px; border-radius:50%; background:#94a3b8; }
      .halo-skill.is-ready .halo-skill-dot { background:#22c55e; box-shadow:0 0 8px rgba(34,197,94,.65); }
      .halo-skill.is-offline .halo-skill-dot { background:#ef4444; }
      .halo-quick-actions { display:flex; flex-wrap:wrap; gap:7px; margin-top:10px; }
      .halo-quick-actions button {
        border:1px solid rgba(255,255,255,.1); border-radius:8px;
        padding:6px 9px; color:inherit; background:rgba(255,255,255,.04); cursor:pointer;
      }
      .halo-quick-actions button:hover { background:rgba(255,255,255,.08); }
    `;
    document.head.appendChild(style);
  }

  function bind() {
    addStyles();

    const form = byId(FORM_ID);
    const input = byId(INPUT_ID);
    if (!form || !input) {
      window.setTimeout(bind, 500);
      return;
    }

    ensureSkillsPanel();
    if (form.dataset.haloV2Bound !== "true") {
      form.dataset.haloV2Bound = "true";
      form.addEventListener("submit", handleSubmit, true);
    }

    healthCheck();
    loadSkills();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }

  window.NoorHALO = {
    send: sendMessage,
    health: healthCheck,
    skills: loadSkills,
    get pendingAction() { return pendingAction; }
  };
})();
