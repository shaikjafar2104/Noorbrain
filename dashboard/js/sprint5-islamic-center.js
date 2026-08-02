(() => {
  "use strict";

  if (window.NoorBrainSprint5Islamic) return;

  const API = "/api/islamic-center-v5";

  const state = {
    center: null,
    prayerState: null,
  };

  const $ = id => document.getElementById(id);

  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      cache: "no-store",
      ...options,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return data;
  }

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function mount() {
    const modules =
      document.querySelector(".nbv2-module-section")
      || document.querySelector("#nbv2Modules")
      || document.querySelector("main");

    if (!modules || $("nbs5IslamicCenter")) return;

    const panel = document.createElement("section");
    panel.id = "nbs5IslamicCenter";
    panel.className = "nbs5-panel";

    panel.innerHTML = `
      <article class="nbs5-card">
        <div class="nbs5-head">
          <div>
            <small>SPRINT 5</small>
            <h2>Islamic Center</h2>
          </div>
          <div class="nbs5-actions">
            <button class="nbs5-button" id="nbs5Refresh">↻</button>
            <button class="nbs5-button primary" id="nbs5AddReminder">＋ Reminder</button>
          </div>
        </div>

        <div class="nbs5-prayer-hero">
          <div>
            <small>Next Prayer</small>
            <h3 id="nbs5NextPrayer">—</h3>
            <span id="nbs5NextTime">—</span>
          </div>
          <div class="nbs5-countdown">
            <small>Countdown</small>
            <b id="nbs5Countdown">—</b>
          </div>
        </div>

        <div class="nbs5-prayer-grid" id="nbs5PrayerGrid"></div>
        <p class="nbs5-status" id="nbs5Status">Loading Islamic Center…</p>
      </article>

      <article class="nbs5-card">
        <div class="nbs5-head">
          <div>
            <small>DAILY</small>
            <h2>Azkar & Duas</h2>
          </div>
        </div>
        <div class="nbs5-item-grid" id="nbs5Items"></div>
      </article>

      <article class="nbs5-card">
        <div class="nbs5-head">
          <div>
            <small>SMART REMINDERS</small>
            <h2>Reminder Rules</h2>
          </div>
        </div>
        <div class="nbs5-reminder-grid" id="nbs5Reminders"></div>
      </article>

      <article class="nbs5-card">
        <div class="nbs5-head">
          <div>
            <small>SETTINGS</small>
            <h2>Prayer & Family</h2>
          </div>
          <div class="nbs5-actions">
            <button class="nbs5-button primary" id="nbs5SaveSettings">Save</button>
          </div>
        </div>

        <div class="nbs5-settings">
          <label>
            Location
            <input id="nbs5Location" placeholder="Toronto">
          </label>

          <label>
            Calculation method
            <select id="nbs5Method">
              <option value="ISNA">ISNA</option>
              <option value="MWL">Muslim World League</option>
              <option value="UmmAlQura">Umm al-Qura</option>
              <option value="Karachi">Karachi</option>
            </select>
          </label>

          <label>
            Madhab
            <select id="nbs5Madhab">
              <option value="Hanafi">Hanafi</option>
              <option value="Standard">Standard</option>
            </select>
          </label>

          <label>
            Ramadan mode
            <select id="nbs5Ramadan">
              <option value="false">Off</option>
              <option value="true">On</option>
            </select>
          </label>

          <label>
            Voice reminders
            <select id="nbs5Voice">
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </label>

          <label>
            Family reminders
            <select id="nbs5Family">
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </label>
        </div>
      </article>
    `;

    modules.insertAdjacentElement("afterend", panel);

    if (!$("nbs5Modal")) {
      const modal = document.createElement("div");
      modal.id = "nbs5Modal";
      modal.className = "nbs5-modal";
      modal.hidden = true;
      document.body.appendChild(modal);
    }

    bind();
    load();
  }

  function bind() {
    $("nbs5Refresh").onclick = load;
    $("nbs5AddReminder").onclick = addReminderModal;
    $("nbs5SaveSettings").onclick = saveSettings;
  }

  async function load() {
    try {
      const payload = await request(`${API}/state`);

      state.center = payload.islamic_center;
      state.prayerState = payload.prayer_state;

      renderPrayer();
      renderItems();
      renderReminders();
      renderSettings();

      $("nbs5Status").textContent =
        `${state.center.reminders.length} reminders · ${state.center.duas.length} duas · ${state.center.azkar.length} azkar`;
    } catch (error) {
      $("nbs5Status").textContent = error.message;
    }
  }

  function renderPrayer() {
    $("nbs5NextPrayer").textContent = state.prayerState.next;
    $("nbs5NextTime").textContent = state.prayerState.next_time;
    $("nbs5Countdown").textContent =
      `${state.prayerState.countdown_minutes} min`;

    $("nbs5PrayerGrid").innerHTML = Object.entries(
      state.center.prayers
    ).map(([name, value]) => `
      <article class="nbs5-prayer">
        <b>${safe(name)}</b>
        <small>${safe(value)}</small>
      </article>
    `).join("");
  }

  function renderItems() {
    const combined = [
      ...state.center.azkar.map(item => ({
        ...item,
        item_type: "azkar",
        icon: "📿",
      })),
      ...state.center.duas.map(item => ({
        ...item,
        item_type: "duas",
        icon: "🤲",
      })),
    ];

    $("nbs5Items").innerHTML = combined.map(item => `
      <article class="nbs5-item ${item.enabled === false ? "disabled" : ""}">
        <span>${item.icon}</span>
        <b>${safe(item.title)}</b>
        <small>${safe(item.category || item.text || "")}</small>
        <button
          class="nbs5-switch"
          data-item-type="${safe(item.item_type)}"
          data-item-id="${safe(item.id)}"
        >
          ${item.enabled === false ? "○" : "●"}
        </button>
      </article>
    `).join("");

    $("nbs5Items").querySelectorAll("[data-item-id]").forEach(button => {
      button.onclick = () => toggleItem(
        button.dataset.itemType,
        button.dataset.itemId
      );
    });
  }

  function renderReminders() {
    const host = $("nbs5Reminders");

    if (!state.center.reminders.length) {
      host.innerHTML = `
        <button class="nbs5-empty" id="nbs5EmptyReminder">
          ＋ Add your first reminder
        </button>
      `;
      $("nbs5EmptyReminder").onclick = addReminderModal;
      return;
    }

    host.innerHTML = state.center.reminders.map(reminder => `
      <article class="nbs5-reminder ${reminder.enabled === false ? "disabled" : ""}">
        <span>🔔</span>
        <b>${safe(reminder.title)}</b>
        <small>${safe(reminder.time || "Context based")} · ${safe(reminder.type)}</small>
        <button
          class="nbs5-switch"
          data-reminder-id="${safe(reminder.id)}"
        >
          ${reminder.enabled === false ? "○" : "●"}
        </button>
      </article>
    `).join("");

    host.querySelectorAll("[data-reminder-id]").forEach(button => {
      button.onclick = () => toggleReminder(button.dataset.reminderId);
    });
  }

  function renderSettings() {
    const settings = state.center.settings;

    $("nbs5Location").value = settings.location || "";
    $("nbs5Method").value = settings.calculation_method || "ISNA";
    $("nbs5Madhab").value = settings.madhab || "Hanafi";
    $("nbs5Ramadan").value = String(settings.ramadan_mode === true);
    $("nbs5Voice").value = String(settings.voice_reminders !== false);
    $("nbs5Family").value = String(settings.family_reminders !== false);
  }

  async function toggleItem(itemType, itemId) {
    try {
      await request(`${API}/items/${itemType}/${itemId}/toggle`, {
        method: "POST",
        body: "{}",
      });

      await load();
    } catch (error) {
      $("nbs5Status").textContent = error.message;
    }
  }

  async function toggleReminder(reminderId) {
    try {
      await request(`${API}/reminders/${reminderId}/toggle`, {
        method: "POST",
        body: "{}",
      });

      await load();
    } catch (error) {
      $("nbs5Status").textContent = error.message;
    }
  }

  async function saveSettings() {
    try {
      await request(`${API}/settings`, {
        method: "POST",
        body: JSON.stringify({
          location: $("nbs5Location").value.trim(),
          calculation_method: $("nbs5Method").value,
          madhab: $("nbs5Madhab").value,
          ramadan_mode: $("nbs5Ramadan").value === "true",
          voice_reminders: $("nbs5Voice").value === "true",
          family_reminders: $("nbs5Family").value === "true",
        }),
      });

      $("nbs5Status").textContent = "Islamic Center settings saved.";
      await load();
    } catch (error) {
      $("nbs5Status").textContent = error.message;
    }
  }

  function modal(html) {
    const host = $("nbs5Modal");
    host.hidden = false;
    host.innerHTML = html;

    host.querySelector("[data-close]")?.addEventListener("click", () => {
      host.hidden = true;
    });
  }

  function addReminderModal() {
    modal(`
      <form class="nbs5-modal-card" id="nbs5ReminderForm">
        <h2>Add Islamic Reminder</h2>

        <label>
          Title
          <input name="title" required placeholder="Evening Azkar">
        </label>

        <label>
          Time
          <input name="time" type="time">
        </label>

        <label>
          Type
          <select name="type">
            <option value="azkar">Azkar</option>
            <option value="dua">Dua</option>
            <option value="prayer">Prayer</option>
            <option value="quran">Quran</option>
            <option value="custom">Custom</option>
          </select>
        </label>

        <label>
          Voice
          <select name="voice">
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </select>
        </label>

        <label>
          Family reminder
          <select name="family">
            <option value="false">No</option>
            <option value="true">Yes</option>
          </select>
        </label>

        <div class="nbs5-modal-actions">
          <button type="button" class="nbs5-button" data-close>Cancel</button>
          <button class="nbs5-button primary" type="submit">Save Reminder</button>
        </div>
      </form>
    `);

    $("nbs5ReminderForm").onsubmit = async event => {
      event.preventDefault();

      const form = Object.fromEntries(
        new FormData(event.target).entries()
      );

      form.voice = form.voice === "true";
      form.family = form.family === "true";

      try {
        await request(`${API}/reminders`, {
          method: "POST",
          body: JSON.stringify(form),
        });

        $("nbs5Modal").hidden = true;
        await load();
      } catch (error) {
        $("nbs5Status").textContent = error.message;
      }
    };
  }

  window.NoorBrainSprint5Islamic = {
    version: "5.0.0",
    load,
    saveSettings,
    toggleReminder,
    toggleItem,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
