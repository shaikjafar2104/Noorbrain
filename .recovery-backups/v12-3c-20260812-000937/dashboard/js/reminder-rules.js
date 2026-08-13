(() => {
  "use strict";

  const API = window.location.origin;
  let currentRules = [];
  let currentMedia = [];
  let refreshTimer = null;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function addStyles() {
    if (document.getElementById(
      "reminderRuleStyles"
    )) return;

    const style = document.createElement("style");
    style.id = "reminderRuleStyles";
    style.textContent = `
      .rr-layout {
        display:grid;
        grid-template-columns:
          minmax(300px,420px) 1fr;
        gap:18px;
      }

      .rr-form {
        display:grid;
        gap:13px;
      }

      .rr-form label {
        display:grid;
        gap:6px;
        font-weight:600;
        font-size:.9rem;
      }

      .rr-form input,
      .rr-form select,
      .rr-form textarea {
        width:100%;
        box-sizing:border-box;
        padding:11px 12px;
        border-radius:9px;
        border:1px solid
          rgba(255,255,255,.12);
        background:rgba(255,255,255,.04);
        color:inherit;
      }

      .rr-form textarea {
        min-height:95px;
        resize:vertical;
      }

      .rr-check {
        display:flex !important;
        grid-template-columns:auto 1fr !important;
        align-items:center;
      }

      .rr-check input {
        width:auto;
      }

      .rr-actions {
        display:flex;
        gap:9px;
        flex-wrap:wrap;
      }

      .rr-card {
        border:1px solid
          rgba(255,255,255,.09);
        border-radius:12px;
        padding:14px;
        margin-bottom:11px;
        background:rgba(255,255,255,.025);
      }

      .rr-card-head {
        display:flex;
        justify-content:space-between;
        align-items:start;
        gap:12px;
      }

      .rr-card h3 {
        margin:0 0 5px;
      }

      .rr-meta {
        opacity:.68;
        font-size:.84rem;
        line-height:1.6;
      }

      .rr-message {
        margin:12px 0;
        padding:10px;
        border-radius:8px;
        background:rgba(255,255,255,.035);
      }

      .rr-history-row {
        padding:11px 4px;
        border-bottom:1px solid
          rgba(255,255,255,.07);
      }

      .rr-history-row:last-child {
        border-bottom:0;
      }

      .rr-history-time {
        opacity:.55;
        font-size:.77rem;
        margin-top:4px;
      }

      .rr-empty {
        text-align:center;
        padding:30px 10px;
        opacity:.58;
      }

      .rr-template-help {
        opacity:.6;
        font-size:.78rem;
        line-height:1.5;
      }

      @media(max-width:900px) {
        .rr-layout {
          grid-template-columns:1fr;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function buildPage() {
    addStyles();

    const nav = document.getElementById("nav");

    if (
      nav &&
      !nav.querySelector(
        '[data-page="reminder-rules"]'
      )
    ) {
      const button =
        document.createElement("button");

      button.className = "nav-item";
      button.dataset.page = "reminder-rules";
      button.innerHTML =
        "🔔 <span>Reminder Rules</span>";

      const settings =
        nav.querySelector(
          '[data-page="settings"]'
        );

      if (settings) {
        nav.insertBefore(button, settings);
      } else {
        nav.appendChild(button);
      }

      button.addEventListener(
        "click",
        openPage
      );
    }

    if (
      document.getElementById(
        "page-reminder-rules"
      )
    ) return;

    const main = document.querySelector(
      "main.main"
    );

    if (!main) return;

    const section =
      document.createElement("section");

    section.id = "page-reminder-rules";
    section.className = "page";

    section.innerHTML = `
      <div class="rr-layout">
        <article class="card">
          <div class="card-head">
            <div>
              <h2>Create Reminder Rule</h2>
              <p>
                Connect an activity event to a
                message or spoken reminder.
              </p>
            </div>
          </div>

          <form id="rrForm" class="rr-form">
            <input
              id="rrId"
              type="hidden"
            >

            <label>
              Rule name
              <input
                id="rrName"
                value="My Reminder"
                required
              >
            </label>

            <label>
              Activity trigger
              <select id="rrTrigger">
                <option value="appeared">
                  Person appeared
                </option>

                <option
                  value="entered_zone"
                  selected
                >
                  Person entered zone
                </option>

                <option value="moved_zone">
                  Person moved to zone
                </option>

                <option value="left_zone">
                  Person left zone
                </option>

                <option value="stayed">
                  Person stayed in zone
                </option>

                <option value="disappeared">
                  Person disappeared
                </option>
              </select>
            </label>

            <label>
              Zone
              <select id="rrZone">
                <option value="">
                  Any zone
                </option>
              </select>
            </label>

            <label>
              Reminder message
              <textarea
                id="rrMessage"
                required
                placeholder="Enter reminder text"
              ></textarea>
            </label>

            <div class="rr-template-help">
              Optional placeholders:
              {person_id}, {zone},
              {previous_zone}, {duration},
              {event}
            </div>

            <label>
              Uploaded audio
              <select id="rrMedia">
                <option value="">
                  No uploaded audio — use speech
                </option>
              </select>
            </label>

            <div class="rr-template-help">
              When uploaded audio is selected,
              NoorBrain plays that file instead of TTS.
            </div>

            <label>
              Cooldown in minutes
              <input
                id="rrCooldown"
                type="number"
                min="0"
                value="30"
              >
            </label>

            <label class="rr-check">
              <input
                id="rrSpeak"
                type="checkbox"
                checked
              >
              Speak through connected speaker
            </label>

            <label class="rr-check">
              <input
                id="rrEnabled"
                type="checkbox"
                checked
              >
              Rule enabled
            </label>

            <div class="rr-actions">
              <button
                type="submit"
                class="button"
              >
                Save Rule
              </button>

              <button
                id="rrCancel"
                type="button"
                class="button secondary"
              >
                Reset
              </button>
            </div>
          </form>
        </article>

        <div>
          <article class="card">
            <div class="card-head">
              <div>
                <h2>Active Rules</h2>
                <p>
                  Dashboard-configured reminder
                  automations
                </p>
              </div>

              <button
                id="rrRefresh"
                class="button secondary"
              >
                Refresh
              </button>
            </div>

            <div id="rrRules">
              <div class="rr-empty">
                No reminder rules yet.
              </div>
            </div>
          </article>

          <article class="card">
            <div class="card-head">
              <div>
                <h2>Reminder History</h2>
                <p>
                  Recently triggered reminders
                </p>
              </div>

              <button
                id="rrClearHistory"
                class="button danger"
              >
                Clear
              </button>
            </div>

            <div id="rrHistory">
              <div class="rr-empty">
                No reminder history yet.
              </div>
            </div>
          </article>
        </div>
      </div>
    `;

    main.appendChild(section);

    document
      .getElementById("rrForm")
      .addEventListener(
        "submit",
        saveRule
      );

    document
      .getElementById("rrCancel")
      .addEventListener(
        "click",
        resetForm
      );

    document
      .getElementById("rrRefresh")
      .addEventListener(
        "click",
        loadData
      );

    document
      .getElementById("rrClearHistory")
      .addEventListener(
        "click",
        clearHistory
      );

    loadZones();
    loadMedia();
  }

  function openPage() {
    document.querySelectorAll(".page")
      .forEach(page => {
        page.classList.remove("active");
      });

    document.querySelectorAll(".nav-item")
      .forEach(item => {
        item.classList.toggle(
          "active",
          item.dataset.page ===
            "reminder-rules"
        );
      });

    document
      .getElementById(
        "page-reminder-rules"
      )
      ?.classList.add("active");

    const title =
      document.getElementById("pageTitle");

    const subtitle =
      document.getElementById(
        "pageSubtitle"
      );

    if (title) {
      title.textContent = "Reminder Rules";
    }

    if (subtitle) {
      subtitle.textContent =
        "Activity-aware reminders controlled " +
        "from the dashboard";
    }

    loadZones();
    loadMedia();
    loadData();

    clearInterval(refreshTimer);

    refreshTimer = setInterval(
      loadData,
      3000
    );
  }

  async function loadZones() {
    const select =
      document.getElementById("rrZone");

    if (!select) return;

    try {
      const response = await fetch(
        `${API}/zones`,
        { cache: "no-store" }
      );

      const data = await response.json();

      const zones = Array.isArray(data)
        ? data
        : (
            Array.isArray(data.zones)
              ? data.zones
              : []
          );

      const current = select.value;

      select.innerHTML =
        '<option value="">Any zone</option>';

      zones.forEach(zone => {
        const name =
          typeof zone === "string"
            ? zone
            : (
                zone.name ||
                zone.id ||
                zone.label
              );

        if (!name) return;

        const option =
          document.createElement("option");

        option.value = name;
        option.textContent = name;

        select.appendChild(option);
      });

      select.value = current;

    } catch (_) {
      // Rules can still use Any zone.
    }
  }

  function mediaName(item) {
    return (
      item.display_name ||
      item.name ||
      item.title ||
      item.original_filename ||
      item.filename ||
      "Unnamed audio"
    );
  }

  function mediaId(item) {
    return (
      item.id ||
      item.media_id ||
      item.uuid ||
      ""
    );
  }

  async function loadMedia(selectedId = null) {
    const select =
      document.getElementById("rrMedia");

    if (!select) return;

    const previous =
      selectedId !== null
        ? selectedId
        : select.value;

    try {
      let response = await fetch(
        `${API}/media`,
        { cache: "no-store" }
      );

      if (!response.ok) {
        response = await fetch(
          `${API}/api/media`,
          { cache: "no-store" }
        );
      }

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const data = await response.json();

      currentMedia = Array.isArray(data)
        ? data
        : (
            Array.isArray(data.items)
              ? data.items
              : (
                  Array.isArray(data.media)
                    ? data.media
                    : (
                        Array.isArray(data.files)
                          ? data.files
                          : []
                      )
                )
          );

      select.innerHTML = `
        <option value="">
          No uploaded audio — use speech
        </option>
      `;

      currentMedia.forEach(item => {
        const id = mediaId(item);

        if (!id) return;

        const option =
          document.createElement("option");

        option.value = id;
        option.textContent = mediaName(item);

        select.appendChild(option);
      });

      if (previous) {
        const exists = currentMedia.some(
          item => mediaId(item) === previous
        );

        if (!exists) {
          const missing =
            document.createElement("option");

          missing.value = previous;
          missing.textContent =
            "⚠ Missing/deleted audio";

          select.appendChild(missing);
        }

        select.value = previous;
      }

    } catch (error) {
      select.innerHTML = `
        <option value="">
          Media Library unavailable
        </option>
      `;

      console.error(
        "Media Library load failed:",
        error
      );
    }
  }

  async function loadData() {
    try {
      const response = await fetch(
        `${API}/reminder-rules?history_limit=50`,
        { cache: "no-store" }
      );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const data = await response.json();

      currentRules = Array.isArray(
        data.rules
      ) ? data.rules : [];

      renderRules(currentRules);

      renderHistory(
        Array.isArray(data.history)
          ? data.history
          : []
      );

    } catch (error) {
      const container =
        document.getElementById("rrRules");

      if (container) {
        container.innerHTML = `
          <div class="rr-empty">
            Reminder API unavailable:
            ${escapeHtml(error.message)}
          </div>
        `;
      }
    }
  }

  function renderRules(rules) {
    const container =
      document.getElementById("rrRules");

    if (!container) return;

    if (!rules.length) {
      container.innerHTML = `
        <div class="rr-empty">
          No reminder rules yet.
        </div>
      `;

      return;
    }

    container.innerHTML = rules.map(rule => `
      <div class="rr-card">
        <div class="rr-card-head">
          <div>
            <h3>
              ${escapeHtml(rule.name)}
            </h3>

            <div class="rr-meta">
              Trigger:
              ${escapeHtml(rule.trigger)}
              <br>

              Zone:
              ${escapeHtml(
                rule.zone || "Any zone"
              )}
              <br>

              Cooldown:
              ${Math.round(
                (rule.cooldown_seconds || 0)
                / 60
              )} minutes
              <br>

              Audio:
              ${escapeHtml(
                rule.media_id
                  ? (
                      mediaName(
                        currentMedia.find(
                          item =>
                            mediaId(item) ===
                            rule.media_id
                        ) || {}
                      ) !== "Unnamed audio"
                        ? mediaName(
                            currentMedia.find(
                              item =>
                                mediaId(item) ===
                                rule.media_id
                            ) || {}
                          )
                        : "Missing/deleted audio"
                    )
                  : (
                      rule.speak
                        ? "Text-to-speech"
                        : "Silent"
                    )
              )}
            </div>
          </div>

          <label class="rr-check">
            <input
              type="checkbox"
              ${rule.enabled ? "checked" : ""}
              onchange="
                window.noorToggleRule(
                  '${rule.id}',
                  this.checked
                )
              "
            >
            Enabled
          </label>
        </div>

        <div class="rr-message">
          ${escapeHtml(rule.message)}
        </div>

        <div class="rr-actions">
          <button
            class="button secondary"
            onclick="
              window.noorEditRule(
                '${rule.id}'
              )
            "
          >
            Edit
          </button>

          <button
            class="button secondary"
            onclick="
              window.noorTestRule(
                '${rule.id}'
              )
            "
          >
            Test
          </button>

          <button
            class="button danger"
            onclick="
              window.noorDeleteRule(
                '${rule.id}'
              )
            "
          >
            Delete
          </button>
        </div>
      </div>
    `).join("");
  }

  function renderHistory(history) {
    const container =
      document.getElementById("rrHistory");

    if (!container) return;

    if (!history.length) {
      container.innerHTML = `
        <div class="rr-empty">
          No reminder history yet.
        </div>
      `;

      return;
    }

    container.innerHTML = history.map(item => `
      <div class="rr-history-row">
        <strong>
          ${escapeHtml(item.message)}
        </strong>

        <div class="rr-meta">
          ${escapeHtml(item.rule_name)}
          · Person
          ${escapeHtml(
            item.person_id ?? "—"
          )}
          ·
          ${escapeHtml(
            item.zone || "No zone"
          )}
          ${
            item.media_played
              ? (
                  " · Played " +
                  escapeHtml(
                    item.media_name ||
                    "uploaded audio"
                  )
                )
              : (
                  item.media_error
                    ? " · Audio failed"
                    : (
                        item.spoken
                          ? " · Spoken"
                          : ""
                      )
                )
          }
          ${
            item.test
              ? " · Test"
              : ""
          }
        </div>

        <div class="rr-history-time">
          ${escapeHtml(item.time_text)}
        </div>
      </div>
    `).join("");
  }

  async function saveRule(event) {
    event.preventDefault();

    const ruleId =
      document.getElementById(
        "rrId"
      ).value;

    const payload = {
      name:
        document.getElementById(
          "rrName"
        ).value.trim(),

      trigger:
        document.getElementById(
          "rrTrigger"
        ).value,

      zone:
        document.getElementById(
          "rrZone"
        ).value || null,

      message:
        document.getElementById(
          "rrMessage"
        ).value.trim(),

      cooldown_seconds:
        Math.max(
          0,
          Number(
            document.getElementById(
              "rrCooldown"
            ).value || 0
          ) * 60
        ),

      speak:
        document.getElementById(
          "rrSpeak"
        ).checked,

      media_id:
        document.getElementById(
          "rrMedia"
        ).value || null,

      enabled:
        document.getElementById(
          "rrEnabled"
        ).checked
    };

    if (!payload.message) {
      alert("Reminder message required.");
      return;
    }

    const url = ruleId
      ? `${API}/reminder-rules/${ruleId}`
      : `${API}/reminder-rules`;

    const method = ruleId
      ? "PUT"
      : "POST";

    const response = await fetch(
      url,
      {
        method,
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      }
    );

    if (!response.ok) {
      const error = await response.text();

      alert(
        `Unable to save rule: ${error}`
      );

      return;
    }

    resetForm();
    await loadData();
  }

  function resetForm() {
    document.getElementById(
      "rrId"
    ).value = "";

    document.getElementById(
      "rrName"
    ).value = "My Reminder";

    document.getElementById(
      "rrTrigger"
    ).value = "entered_zone";

    document.getElementById(
      "rrZone"
    ).value = "";

    document.getElementById(
      "rrMessage"
    ).value = "";

    document.getElementById(
      "rrCooldown"
    ).value = "30";

    document.getElementById(
      "rrSpeak"
    ).checked = true;

    document.getElementById(
      "rrMedia"
    ).value = "";

    document.getElementById(
      "rrEnabled"
    ).checked = true;
  }

  window.noorEditRule = ruleId => {
    const rule = currentRules.find(
      item => item.id === ruleId
    );

    if (!rule) return;

    document.getElementById(
      "rrId"
    ).value = rule.id;

    document.getElementById(
      "rrName"
    ).value = rule.name;

    document.getElementById(
      "rrTrigger"
    ).value = rule.trigger;

    document.getElementById(
      "rrZone"
    ).value = rule.zone || "";

    document.getElementById(
      "rrMessage"
    ).value = rule.message;

    document.getElementById(
      "rrCooldown"
    ).value = Math.round(
      (rule.cooldown_seconds || 0) / 60
    );

    document.getElementById(
      "rrSpeak"
    ).checked = rule.speak;

    loadMedia(rule.media_id || "");

    document.getElementById(
      "rrEnabled"
    ).checked = rule.enabled;

    document.getElementById(
      "rrName"
    ).scrollIntoView({
      behavior: "smooth",
      block: "center"
    });
  };

  window.noorToggleRule =
    async (ruleId, enabled) => {
      await fetch(
        `${API}/reminder-rules/` +
        `${ruleId}/toggle`,
        {
          method: "PATCH",
          headers: {
            "Content-Type":
              "application/json"
          },
          body: JSON.stringify({
            enabled
          })
        }
      );

      await loadData();
    };

  window.noorTestRule =
    async ruleId => {
      const response = await fetch(
        `${API}/reminder-rules/` +
        `${ruleId}/test`,
        {
          method: "POST"
        }
      );

      if (!response.ok) {
        alert("Reminder test failed.");
        return;
      }

      await loadData();
    };

  window.noorDeleteRule =
    async ruleId => {
      if (!confirm(
        "Delete this reminder rule?"
      )) return;

      await fetch(
        `${API}/reminder-rules/${ruleId}`,
        {
          method: "DELETE"
        }
      );

      resetForm();
      await loadData();
    };

  async function clearHistory() {
    if (!confirm(
      "Clear reminder history?"
    )) return;

    await fetch(
      `${API}/reminder-history/clear`,
      {
        method: "POST"
      }
    );

    await loadData();
  }

  document.addEventListener(
    "click",
    event => {
      const item =
        event.target.closest(".nav-item");

      if (
        item &&
        item.dataset.page !==
          "reminder-rules"
      ) {
        clearInterval(refreshTimer);
        refreshTimer = null;
      }
    }
  );

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      buildPage
    );
  } else {
    buildPage();
  }
})();
