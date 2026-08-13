(() => {
  "use strict";

  if (window.NoorMobileRulesV12) return;

  const API = "/reminder-rules";
  let rules = [];
  let editing = null;

  const $ = id => document.getElementById(id);

  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      })[c]
    );

  async function request(path = "", options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    const data =
      await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail || `HTTP ${response.status}`
      );
    }

    return data;
  }

  function createPanel() {
    if ($("nbRulesV12")) return;

    const panel = document.createElement("div");

    panel.id = "nbRulesV12";
    panel.hidden = true;

    panel.innerHTML = `
      <div class="nbr-shell">

        <header class="nbr-head">
          <button id="nbrBack"
                  class="nbr-back"
                  type="button">‹</button>

          <div>
            <small>AUTOMATION</small>
            <h2>Reminder Rules</h2>
          </div>

          <button id="nbrNew"
                  class="nbr-new"
                  type="button">
            + New
          </button>
        </header>

        <main class="nbr-main">

          <section class="nbr-summary">
            <div>
              <strong id="nbrCount">—</strong>
              <span>Rules</span>
            </div>

            <div>
              <strong id="nbrEnabled">—</strong>
              <span>Enabled</span>
            </div>

            <div>
              <strong id="nbrEngine">—</strong>
              <span>Engine</span>
            </div>
          </section>

          <div id="nbrStatus"
               class="nbr-status">
            Loading…
          </div>

          <section id="nbrEditor"
                   class="nbr-editor"
                   hidden>

            <div class="nbr-editor-head">
              <h3 id="nbrEditorTitle">
                New Reminder Rule
              </h3>

              <button id="nbrCancel"
                      type="button">
                ×
              </button>
            </div>

            <label>
              Rule name
              <input id="nbrName"
                     placeholder="Kitchen Dua">
            </label>

            <label>
              Trigger
              <select id="nbrTrigger">
                <option value="appeared">
                  Person appeared
                </option>

                <option value="entered_zone">
                  Entered zone
                </option>

                <option value="moved_zone">
                  Moved zone
                </option>

                <option value="left_zone">
                  Left zone
                </option>

                <option value="stayed">
                  Stayed
                </option>

                <option value="disappeared">
                  Person disappeared
                </option>
              </select>
            </label>

            <label>
              Zone
              <input id="nbrZone"
                     placeholder="Optional — Hall, Kitchen">
            </label>

            <label>
              Noor message
              <textarea id="nbrMessage"
                        rows="3"
                        placeholder="What should Noor say?"></textarea>
            </label>

            <label>
              Cooldown
              <select id="nbrCooldown">
                <option value="60">1 minute</option>
                <option value="300">5 minutes</option>
                <option value="900">15 minutes</option>
                <option value="1800" selected>
                  30 minutes
                </option>
                <option value="3600">1 hour</option>
                <option value="10800">3 hours</option>
                <option value="21600">6 hours</option>
                <option value="86400">24 hours</option>
              </select>
            </label>

            <label class="nbr-switch-row">
              <span>
                <b>Noor Speak</b>
                <small>
                  Speak the reminder aloud
                </small>
              </span>

              <input id="nbrSpeak"
                     type="checkbox"
                     checked>
            </label>

            <label>
              Media ID
              <input id="nbrMedia"
                     placeholder="Optional audio/media ID">
            </label>

            <label class="nbr-switch-row">
              <span>
                <b>Enabled</b>
                <small>
                  Rule can trigger automatically
                </small>
              </span>

              <input id="nbrRuleEnabled"
                     type="checkbox"
                     checked>
            </label>

            <button id="nbrSave"
                    class="nbr-primary"
                    type="button">
              Save Rule
            </button>

          </section>

          <section>
            <div class="nbr-section-head">
              <h3>My Rules</h3>

              <button id="nbrRefresh"
                      type="button">
                Refresh
              </button>
            </div>

            <div id="nbrList"
                 class="nbr-list"></div>
          </section>

        </main>

      </div>
    `;

    document.body.appendChild(panel);

    const style =
      document.createElement("style");

    style.textContent = `
      #nbRulesV12 {
        position: fixed;
        inset: 0;
        z-index: 2147483000;
        background: #081525;
        color: #f5f8fc;
        overflow: auto;
        font-family:
          system-ui,-apple-system,BlinkMacSystemFont,
          "Segoe UI",sans-serif;
      }

      .nbr-shell {
        max-width: 760px;
        margin: auto;
        min-height: 100vh;
        background:
          linear-gradient(180deg,#0d2037,#081525);
      }

      .nbr-head {
        position: sticky;
        top: 0;
        z-index: 4;
        display: grid;
        grid-template-columns: auto 1fr auto;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: rgba(9,25,43,.96);
        backdrop-filter: blur(16px);
        border-bottom:
          1px solid rgba(255,255,255,.07);
      }

      .nbr-head h2 {
        margin: 2px 0 0;
        font-size: 20px;
      }

      .nbr-head small {
        opacity: .55;
        font-size: 10px;
        letter-spacing: .12em;
      }

      .nbr-back,
      .nbr-new,
      #nbrRefresh,
      #nbrCancel {
        border: 0;
        border-radius: 11px;
        background: #1b3553;
        color: white;
        padding: 9px 12px;
        font-weight: 700;
      }

      .nbr-back {
        font-size: 25px;
        padding: 3px 13px;
      }

      .nbr-new {
        background: #2d8cff;
      }

      .nbr-main {
        padding: 15px;
      }

      .nbr-summary {
        display: grid;
        grid-template-columns:
          repeat(3,minmax(0,1fr));
        gap: 9px;
        margin-bottom: 12px;
      }

      .nbr-summary > div {
        background: #102640;
        border:
          1px solid rgba(255,255,255,.06);
        border-radius: 14px;
        padding: 13px;
      }

      .nbr-summary strong,
      .nbr-summary span {
        display: block;
      }

      .nbr-summary strong {
        font-size: 20px;
      }

      .nbr-summary span {
        opacity: .58;
        font-size: 11px;
        margin-top: 2px;
      }

      .nbr-status {
        margin-bottom: 12px;
        padding: 10px 12px;
        border-radius: 12px;
        background: rgba(110,231,168,.08);
        color: #8bf0b7;
        font-size: 12px;
      }

      .nbr-editor {
        margin-bottom: 18px;
        padding: 15px;
        border-radius: 16px;
        background: #102640;
        border:
          1px solid rgba(255,255,255,.07);
      }

      .nbr-editor-head,
      .nbr-section-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
      }

      .nbr-editor h3,
      .nbr-section-head h3 {
        margin: 0;
      }

      .nbr-editor label {
        display: block;
        margin-top: 13px;
        font-size: 12px;
        color: rgba(255,255,255,.72);
      }

      .nbr-editor input:not([type=checkbox]),
      .nbr-editor select,
      .nbr-editor textarea {
        box-sizing: border-box;
        width: 100%;
        margin-top: 6px;
        padding: 11px 12px;
        border-radius: 11px;
        border:
          1px solid rgba(255,255,255,.09);
        background: #091a2d;
        color: white;
        font: inherit;
      }

      .nbr-switch-row {
        display: flex !important;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 10px 0;
      }

      .nbr-switch-row b,
      .nbr-switch-row small {
        display: block;
      }

      .nbr-switch-row small {
        opacity: .6;
        margin-top: 2px;
      }

      .nbr-switch-row input {
        width: 22px;
        height: 22px;
      }

      .nbr-primary {
        width: 100%;
        margin-top: 15px;
        padding: 12px;
        border: 0;
        border-radius: 12px;
        background: #2d8cff;
        color: white;
        font-weight: 800;
      }

      #nbrRefresh {
        padding: 7px 10px;
        font-size: 11px;
      }

      .nbr-list {
        display: grid;
        gap: 10px;
        margin-top: 10px;
        padding-bottom: 30px;
      }

      .nbr-card {
        padding: 14px;
        border-radius: 15px;
        background: #102640;
        border:
          1px solid rgba(255,255,255,.06);
      }

      .nbr-card.off {
        opacity: .62;
      }

      .nbr-card-head {
        display: flex;
        justify-content: space-between;
        gap: 10px;
      }

      .nbr-card h4 {
        margin: 0 0 4px;
        font-size: 15px;
      }

      .nbr-card p {
        margin: 7px 0;
        color: rgba(255,255,255,.68);
        font-size: 12px;
      }

      .nbr-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
      }

      .nbr-meta span {
        padding: 4px 7px;
        border-radius: 999px;
        background: rgba(255,255,255,.06);
        font-size: 10px;
      }

      .nbr-card-actions {
        display: grid;
        grid-template-columns:
          repeat(4,minmax(0,1fr));
        gap: 6px;
        margin-top: 11px;
      }

      .nbr-card-actions button {
        border: 0;
        border-radius: 9px;
        padding: 8px 5px;
        background: #1b3553;
        color: white;
        font-size: 11px;
        font-weight: 700;
      }

      .nbr-card-actions .danger {
        background: rgba(255,90,90,.14);
        color: #ff9696;
      }

      .nbr-empty {
        padding: 28px 14px;
        text-align: center;
        border-radius: 14px;
        background: #102640;
        opacity: .65;
      }
    `;

    document.head.appendChild(style);

    $("nbrBack").onclick = close;
    $("nbrNew").onclick = newRule;
    $("nbrCancel").onclick = closeEditor;
    $("nbrRefresh").onclick = load;
    $("nbrSave").onclick = save;

    $("nbrList").addEventListener(
      "click",
      handleAction
    );
  }

  function status(text, error = false) {
    const node = $("nbrStatus");
    if (!node) return;

    node.textContent = text;
    node.style.color =
      error ? "#ff9b9b" : "#8bf0b7";
  }

  async function load() {
    status("Loading rules…");

    try {
      const data = await request(
        "?history_limit=30"
      );

      rules = data.rules || [];

      $("nbrCount").textContent =
        data.rule_count ?? rules.length;

      $("nbrEnabled").textContent =
        rules.filter(x => x.enabled).length;

      $("nbrEngine").textContent =
        data.status || "ready";

      render();

      status(
        `${rules.length} rules synchronized`
      );
    } catch (error) {
      status(error.message, true);
    }
  }

  function render() {
    const box = $("nbrList");

    if (!rules.length) {
      box.innerHTML =
        `<div class="nbr-empty">
          No reminder rules yet.
        </div>`;
      return;
    }

    box.innerHTML = rules.map(rule => `
      <article class="nbr-card
        ${rule.enabled ? "" : "off"}">

        <div class="nbr-card-head">
          <div>
            <h4>${esc(rule.name)}</h4>

            <div class="nbr-meta">
              <span>
                ${esc(rule.trigger)}
              </span>

              ${rule.zone
                ? `<span>${esc(rule.zone)}</span>`
                : ""}

              <span>
                ${rule.speak ? "🔊 Speak" : "🔇 No speech"}
              </span>
            </div>
          </div>

          <strong>
            ${rule.enabled ? "ON" : "OFF"}
          </strong>
        </div>

        <p>
          ${esc(rule.message || "No message")}
        </p>

        <div class="nbr-meta">
          <span>
            Cooldown:
            ${Math.round(
              Number(rule.cooldown_seconds || 0) / 60
            )} min
          </span>

          ${rule.media_id
            ? `<span>▶ Media</span>`
            : ""}
        </div>

        <div class="nbr-card-actions">
          <button data-action="toggle"
                  data-id="${esc(rule.id)}">
            ${rule.enabled ? "Disable" : "Enable"}
          </button>

          <button data-action="edit"
                  data-id="${esc(rule.id)}">
            Edit
          </button>

          <button data-action="test"
                  data-id="${esc(rule.id)}">
            Test
          </button>

          <button class="danger"
                  data-action="delete"
                  data-id="${esc(rule.id)}">
            Delete
          </button>
        </div>
      </article>
    `).join("");
  }

  function newRule() {
    editing = null;

    $("nbrEditorTitle").textContent =
      "New Reminder Rule";

    $("nbrName").value = "";
    $("nbrTrigger").value = "appeared";
    $("nbrZone").value = "";
    $("nbrMessage").value = "";
    $("nbrCooldown").value = "1800";
    $("nbrSpeak").checked = true;
    $("nbrMedia").value = "";
    $("nbrRuleEnabled").checked = true;

    $("nbrEditor").hidden = false;

    $("nbrEditor").scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  function editRule(id) {
    const rule =
      rules.find(item => item.id === id);

    if (!rule) return;

    editing = id;

    $("nbrEditorTitle").textContent =
      "Edit Reminder Rule";

    $("nbrName").value =
      rule.name || "";

    $("nbrTrigger").value =
      rule.trigger || "appeared";

    $("nbrZone").value =
      rule.zone || "";

    $("nbrMessage").value =
      rule.message || "";

    $("nbrCooldown").value =
      String(rule.cooldown_seconds || 1800);

    $("nbrSpeak").checked =
      Boolean(rule.speak);

    $("nbrMedia").value =
      rule.media_id || "";

    $("nbrRuleEnabled").checked =
      Boolean(rule.enabled);

    $("nbrEditor").hidden = false;

    $("nbrEditor").scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  function closeEditor() {
    editing = null;
    $("nbrEditor").hidden = true;
  }

  async function save() {
    const name =
      $("nbrName").value.trim();

    const message =
      $("nbrMessage").value.trim();

    if (!name) {
      status("Rule name is required.", true);
      return;
    }

    const payload = {
      name,
      trigger: $("nbrTrigger").value,
      zone:
        $("nbrZone").value.trim() || null,
      message,
      cooldown_seconds:
        Number($("nbrCooldown").value),
      speak: $("nbrSpeak").checked,
      media_id:
        $("nbrMedia").value.trim() || null,
      enabled:
        $("nbrRuleEnabled").checked
    };

    status(
      editing
        ? "Updating rule…"
        : "Creating rule…"
    );

    try {
      await request(
        editing
          ? `/${encodeURIComponent(editing)}`
          : "",
        {
          method: editing ? "PUT" : "POST",
          body: JSON.stringify(payload)
        }
      );

      closeEditor();
      await load();

      status(
        editing
          ? "Rule updated."
          : "Rule created."
      );

    } catch (error) {
      status(error.message, true);
    }
  }

  async function toggleRule(id) {
    const rule=rules.find(item=>String(item.id)===String(id));

    if(!rule){
      status("Reminder rule not found.", true);
      return;
    }

    try {
      status("Updating rule…");

      await request(
        `/${encodeURIComponent(id)}/toggle`,
        {
          method: "PATCH",
          body: JSON.stringify({enabled:!rule.enabled})
        }
      );

      await load();

    } catch (error) {
      status(error.message, true);
    }
  }

  async function testRule(id) {
    try {
      status("Testing rule…");

      const data = await request(
        `/${encodeURIComponent(id)}/test`,
        { method: "POST" }
      );

      status(
        data.status
          ? `Test: ${data.status}`
          : "Rule test completed."
      );

    } catch (error) {
      status(error.message, true);
    }
  }

  async function deleteRule(id) {
    const rule =
      rules.find(item => item.id === id);

    if (!confirm(
      `Delete "${rule?.name || "this rule"}"?`
    )) return;

    try {
      status("Deleting rule…");

      await request(
        `/${encodeURIComponent(id)}`,
        { method: "DELETE" }
      );

      await load();

      status("Rule deleted.");

    } catch (error) {
      status(error.message, true);
    }
  }

  function handleAction(event) {
    const button =
      event.target.closest("button[data-action]");

    if (!button) return;

    const id = button.dataset.id;

    switch (button.dataset.action) {
      case "toggle":
        toggleRule(id);
        break;

      case "edit":
        editRule(id);
        break;

      case "test":
        testRule(id);
        break;

      case "delete":
        deleteRule(id);
        break;
    }
  }

  async function open(target = null) {
    createPanel();

    $("nbRulesV12").hidden = false;
    document.body.style.overflow = "hidden";

    closeEditor();
    await load();

    if (target === "new") {
      newRule();
    } else if (target) {
      editRule(String(target));
    }
  }

  function close() {
    $("nbRulesV12").hidden = true;
    document.body.style.overflow = "";
  }

  createPanel();

  window.NoorMobileRulesV12 = Object.freeze({
    installed: true,
    version: "12.0.0",
    open,
    close,
    load
  });

  console.log(
    "NOOR_MOBILE_RULES_V12_READY"
  );
})();
