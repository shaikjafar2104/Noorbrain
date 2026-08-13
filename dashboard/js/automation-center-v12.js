(() => {
"use strict";

if (window.NoorAutomationCenterV12) return;

const API = {
  smart: "/api/smart-automation/rules",
  scenes: "/api/automation/scenes",
  groups: "/api/automation/groups",
  routines: "/api/automation/routines",
  reminders: "/reminder-rules"
};

const state = {
  open: false,
  tab: "smart",
  data: {
    smart: [],
    scenes: [],
    groups: [],
    routines: [],
    reminders: []
  }
};

const $ = id => document.getElementById(id);

async function request(url, options={}) {
  const r = await fetch(url, {
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await r.json().catch(() => ({}));

  if (!r.ok) {
    throw new Error(
      data.detail ||
      data.message ||
      `HTTP ${r.status}`
    );
  }

  return data;
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;");
}

function createUI() {
  if ($("nbAutomationCenterV12")) return;

  const root = document.createElement("div");
  root.id = "nbAutomationCenterV12";
  root.hidden = true;

  root.innerHTML = `
    <div class="nbac-shell">

      <header class="nbac-header">
        <div>
          <div class="nbac-eyebrow">NOORBRAIN</div>
          <h2>Automation Center</h2>
          <p>
            Rules, scenes, device groups and routines
            in one place.
          </p>
        </div>

        <button
          id="nbacClose"
          class="nbac-icon"
          type="button"
          aria-label="Close"
        >✕</button>
      </header>

      <nav class="nbac-tabs">
        <button data-nbac-tab="smart">
          <span>⚡</span>
          Smart Rules
          <b id="nbacCountSmart">0</b>
        </button>

        <button data-nbac-tab="scenes">
          <span>◈</span>
          Scenes
          <b id="nbacCountScenes">0</b>
        </button>

        <button data-nbac-tab="groups">
          <span>⌂</span>
          Groups
          <b id="nbacCountGroups">0</b>
        </button>

        <button data-nbac-tab="routines">
          <span>↻</span>
          Routines
          <b id="nbacCountRoutines">0</b>
        </button>

        <button data-nbac-tab="reminders">
          <span>🕌</span>
          Reminder Rules
          <b id="nbacCountReminders">0</b>
        </button>
      </nav>

      <section class="nbac-toolbar">
        <div>
          <strong id="nbacTitle">Smart Rules</strong>
          <span id="nbacStatus">Ready</span>
        </div>

        <div class="nbac-toolbar-actions">
          <button id="nbacRefresh" type="button">
            ↻ Refresh
          </button>

          <button
            id="nbacAdd"
            class="primary"
            type="button"
          >
            ＋ Add
          </button>
        </div>
      </section>

      <main
        id="nbacContent"
        class="nbac-content"
      ></main>

    </div>
  `;

  document.body.appendChild(root);

  $("nbacClose").onclick = close;
  $("nbacRefresh").onclick = load;

  $("nbacAdd").onclick = () => {
    document.dispatchEvent(
      new CustomEvent(
        "noorbrain:automation-add",
        { detail: { tab: state.tab } }
      )
    );
  };

  root.querySelectorAll("[data-nbac-tab]")
    .forEach(button => {
      button.onclick = () =>
        select(button.dataset.nbacTab);
    });
}

function titleFor(tab) {
  return {
    smart: "Smart Rules",
    scenes: "Scenes",
    groups: "Device Groups",
    routines: "Routines",
    reminders: "Reminder Rules"
  }[tab] || "Automation";
}

function emptyMessage(tab) {
  return {
    smart:
      "No smart automation rules yet.",
    scenes:
      "No scenes yet. Scenes combine actions into one command.",
    groups:
      "No device groups yet.",
    routines:
      "No routines yet. Routines run scenes on a schedule.",
    reminders:
      "No reminder rules configured."
  }[tab];
}

function card(item, tab) {
  const name = esc(
    item.name ||
    item.title ||
    "Unnamed"
  );

  let meta = "";

  if (tab === "smart") {
    meta =
      `${item.enabled === false ? "Disabled" : "Enabled"} · ` +
      `${(item.actions || []).length} actions`;
  }

  if (tab === "scenes") {
    meta =
      `${item.enabled === false ? "Disabled" : "Enabled"} · ` +
      `${(item.actions || []).length} actions · ` +
      `${item.run_count || 0} runs`;
  }

  if (tab === "groups") {
    meta =
      `${esc(item.room || "Unassigned")} · ` +
      `${(item.device_ids || []).length} devices`;
  }

  if (tab === "routines") {
    meta =
      `${esc(item.schedule || "No schedule")} · ` +
      `${item.enabled === false ? "Disabled" : "Enabled"} · ` +
      `${item.run_count || 0} runs`;
  }

  if (tab === "reminders") {
    meta =
      `${esc(item.trigger || "trigger")} · ` +
      `${item.enabled === false ? "Disabled" : "Enabled"}`;
  }

  return `
    <article
      class="nbac-card"
      data-id="${esc(item.id)}"
    >
      <div class="nbac-card-main">
        <strong>${name}</strong>
        <small>${meta}</small>
      </div>

      <div class="nbac-card-actions">

        ${
          ["smart","scenes","routines","reminders"].includes(tab)
          ? `
            <button
              data-action="toggle"
              data-id="${esc(item.id)}"
              type="button"
            >${item.enabled === false ? "Enable" : "Disable"}</button>
          `
          : ""
        }

        ${
          ["smart","scenes","routines"].includes(tab)
          ? `
            <button
              data-action="run"
              data-id="${esc(item.id)}"
              type="button"
            >▶ Run</button>
          `
          : ""
        }

        <button
          data-action="edit"
          data-id="${esc(item.id)}"
          type="button"
        >Edit</button>

        <button
          data-action="delete"
          data-id="${esc(item.id)}"
          class="danger"
          type="button"
        >Delete</button>

      </div>
    </article>
  `;
}

function render() {
  const items = state.data[state.tab] || [];

  $("nbacTitle").textContent =
    titleFor(state.tab);

  document
    .querySelectorAll("[data-nbac-tab]")
    .forEach(button => {
      button.classList.toggle(
        "active",
        button.dataset.nbacTab === state.tab
      );
    });

  if (!items.length) {
    $("nbacContent").innerHTML = `
      <div class="nbac-empty">
        <div>◇</div>
        <strong>${titleFor(state.tab)}</strong>
        <p>${emptyMessage(state.tab)}</p>
        <button
          type="button"
          class="primary"
          id="nbacEmptyAdd"
        >
          ＋ Add ${titleFor(state.tab)}
        </button>
      </div>
    `;

    $("nbacEmptyAdd").onclick =
      () => $("nbacAdd").click();

    return;
  }

  $("nbacContent").innerHTML =
    `<div class="nbac-list">
      ${items.map(x => card(x,state.tab)).join("")}
    </div>`;

  $("nbacContent")
    .querySelectorAll("[data-action]")
    .forEach(button => {
      button.onclick = () => action(
        button.dataset.action,
        button.dataset.id
      );
    });
}

async function action(type,id) {
  const item = state.data[state.tab]
    .find(x => String(x.id) === String(id));

  if (!item) return;

  if (type === "delete") {
    if (!confirm(`Delete "${item.name}"?`))
      return;

    const path = {
      smart:
        `${API.smart}/${id}`,
      scenes:
        `${API.scenes}/${id}`,
      groups:
        `${API.groups}/${id}`,
      routines:
        `${API.routines}/${id}`,
      reminders:
        `${API.reminders}/${id}`
    }[state.tab];

    try {
      $("nbacStatus").textContent =
        "Deleting…";

      await request(path,{
        method:"DELETE"
      });

      await load();
    } catch (e) {
      $("nbacStatus").textContent =
        "Delete failed";
      alert(e.message);
    }

    return;
  }

  if (type === "toggle") {
    const enabled=item.enabled === false;
    const path={
      smart:`${API.smart}/${id}`,
      scenes:`${API.scenes}/${id}`,
      routines:`${API.routines}/${id}`,
      reminders:`${API.reminders}/${id}/toggle`
    }[state.tab];

    if(!path) return;

    try {
      $("nbacStatus").textContent="Updating…";
      await request(path,{
        method:"PATCH",
        body:JSON.stringify({enabled})
      });
      await load();
    } catch(e) {
      $("nbacStatus").textContent="Update failed";
      alert(e.message);
    }

    return;
  }

  if (type === "run") {
    const path = {
      smart:
        `${API.smart}/${id}/run`,
      scenes:
        `${API.scenes}/${id}/execute`,
      routines:
        `${API.routines}/${id}/run`
    }[state.tab];

    if (!path) return;

    try {
      $("nbacStatus").textContent =
        "Running…";

      const options = {
        method:"POST"
      };

      if (state.tab === "smart") {
        options.body =
          JSON.stringify({confirmed:true});
      }

      const result=await request(path,options);
      const failure=executionFailure(result,state.tab);

      if(failure){
        throw new Error(failure);
      }

      $("nbacStatus").textContent =
        "Run complete";

      await load();
    } catch (e) {
      $("nbacStatus").textContent =
        "Run failed";
      alert(e.message);
    }

    return;
  }

  if (type === "edit") {
    document.dispatchEvent(
      new CustomEvent(
        "noorbrain:automation-edit",
        {
          detail: {
            tab: state.tab,
            item
          }
        }
      )
    );
  }
}

function executionFailure(result,tab) {
  const status=String(result?.status || "").toLowerCase();

  if(["failed","error","execution_failed","needs_confirmation"].includes(status)){
    return result?.detail || result?.message || `Execution ${status.replaceAll("_"," ")}.`;
  }

  const scene=tab === "routines"
    ? result?.scene_result
    : result;

  if((tab === "scenes" || tab === "routines") && scene){
    const errors=Number(scene.error_count || 0);
    const successes=Number(scene.success_count || 0);

    if(errors > 0 || successes < 1){
      const first=(scene.results || []).find(item=>item.status !== "ok");
      return first?.reason || "No scene action executed successfully.";
    }
  }

  return "";
}

async function load() {
  createUI();

  $("nbacStatus").textContent =
    "Loading…";

  try {
    const [
      smart,
      scenes,
      groups,
      routines,
      reminders
    ] = await Promise.all([
      request(API.smart),
      request(API.scenes),
      request(API.groups),
      request(API.routines),
      request(API.reminders)
    ]);

    state.data.smart =
      smart.rules || [];

    state.data.scenes =
      scenes.scenes || [];

    state.data.groups =
      groups.groups || [];

    state.data.routines =
      routines.routines || [];

    state.data.reminders =
      reminders.rules || [];

    $("nbacCountSmart").textContent =
      state.data.smart.length;

    $("nbacCountScenes").textContent =
      state.data.scenes.length;

    $("nbacCountGroups").textContent =
      state.data.groups.length;

    $("nbacCountRoutines").textContent =
      state.data.routines.length;

    $("nbacCountReminders").textContent =
      state.data.reminders.length;

    $("nbacStatus").textContent =
      "Live";

    render();

  } catch (e) {
    $("nbacStatus").textContent =
      "Unavailable";

    $("nbacContent").innerHTML = `
      <div class="nbac-empty">
        <strong>Automation unavailable</strong>
        <p>${esc(e.message)}</p>
      </div>
    `;
  }
}

function select(tab) {
  if (!state.data[tab]) return;

  state.tab = tab;
  render();
}

async function open(tab="smart") {
  createUI();

  state.open = true;
  state.tab =
    state.data[tab] ? tab : "smart";

  $("nbAutomationCenterV12").hidden =
    false;

  document.body.classList.add(
    "nb-automation-open"
  );

  await load();
  select(state.tab);
}

function close() {
  state.open = false;

  $("nbAutomationCenterV12").hidden =
    true;

  document.body.classList.remove(
    "nb-automation-open"
  );
}

createUI();

window.NoorAutomationCenterV12 = {
  version:"12.3.0",
  open,
  close,
  load,
  select,
  state
};

console.log(
  "NOOR_AUTOMATION_CENTER_V12_READY"
);

})();

/* ===== V12.3-I PRODUCT FORMS ===== */
(() => {
"use strict";

if (window.NoorAutomationFormsV12) return;

const API = {
  smart: "/api/smart-automation/rules",
  scenes: "/api/automation/scenes",
  groups: "/api/automation/groups",
  routines: "/api/automation/routines",
  devices: "/api/devices"
};

let editing = null;
let devices = [];

const $ = id => document.getElementById(id);

function esc(v) {
  return String(v ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;");
}

async function api(url, options={}) {
  const r = await fetch(url,{
    cache:"no-store",
    headers:{
      "Content-Type":"application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await r.json().catch(() => ({}));

  if (!r.ok) {
    throw new Error(
      data.detail ||
      data.message ||
      `HTTP ${r.status}`
    );
  }

  return data;
}

function createSheet() {
  if ($("nbAutomationFormV12")) return;

  const root=document.createElement("div");

  root.id="nbAutomationFormV12";
  root.hidden=true;

  root.innerHTML=`
    <div class="nbaf-backdrop"></div>

    <section class="nbaf-sheet">
      <header class="nbaf-header">
        <div>
          <small>AUTOMATION</small>
          <h3 id="nbafTitle">Add</h3>
        </div>

        <button
          id="nbafClose"
          type="button"
          aria-label="Close"
        >✕</button>
      </header>

      <form id="nbafForm">
        <div id="nbafFields"></div>

        <div
          id="nbafMessage"
          class="nbaf-message"
        ></div>

        <footer class="nbaf-actions">
          <button
            id="nbafCancel"
            type="button"
          >Cancel</button>

          <button
            id="nbafSave"
            type="submit"
            class="primary"
          >Save</button>
        </footer>
      </form>
    </section>
  `;

  document.body.appendChild(root);

  $("nbafClose").onclick=close;
  $("nbafCancel").onclick=close;

  root.querySelector(".nbaf-backdrop")
    .onclick=close;

  $("nbafForm").onsubmit=save;
}

function field(label,html,help="") {
  return `
    <label class="nbaf-field">
      <span>${label}</span>
      ${html}
      ${help ? `<small>${help}</small>` : ""}
    </label>
  `;
}

function input(id,value="",type="text",required=false) {
  return `
    <input
      id="${id}"
      type="${type}"
      value="${esc(value)}"
      ${required ? "required" : ""}
      autocomplete="off"
    >
  `;
}

function checkbox(id,checked=true,label="Enabled") {
  return `
    <label class="nbaf-check">
      <input
        id="${id}"
        type="checkbox"
        ${checked ? "checked" : ""}
      >
      <span>${label}</span>
    </label>
  `;
}

function deviceOptions(selected="") {
  if (!devices.length) {
    return `
      <option value="">
        No devices configured
      </option>
    `;
  }

  return devices.map(d => {
    const id=d.id || d.device_id || "";
    const name=d.name || d.label || id;

    return `
      <option
        value="${esc(id)}"
        ${String(id)===String(selected) ? "selected" : ""}
      >
        ${esc(name)}
      </option>
    `;
  }).join("");
}

function sceneOptions(selected="") {
  const scenes=
    window.NoorAutomationCenterV12
      ?.state?.data?.scenes || [];

  if (!scenes.length) {
    return `
      <option value="">
        Create a Scene first
      </option>
    `;
  }

  return scenes.map(s => `
    <option
      value="${esc(s.id)}"
      ${String(s.id)===String(selected) ? "selected" : ""}
    >
      ${esc(s.name)}
    </option>
  `).join("");
}

function smartFields(item={}) {
  const action=(item.actions || [])[0] || {};
  const actionText=
    action.kind === "halo" && action.name === "speak"
      ? action.arguments?.text || ""
      : "";

  return `
    ${field(
      "Rule name",
      input("nbafName",item.name,"text",true)
    )}

    ${field(
      "Description",
      `<textarea id="nbafDescription">${esc(
        item.description || ""
      )}</textarea>`
    )}

    ${field(
      "Condition mode",
      `<select id="nbafConditionMode">
        <option
          value="all"
          ${item.condition_mode!=="any" ? "selected" : ""}
        >All conditions</option>
        <option
          value="any"
          ${item.condition_mode==="any" ? "selected" : ""}
        >Any condition</option>
      </select>`
    )}

    ${field(
      "HALO speech action",
      `<textarea id="nbafActionText" placeholder="What HALO should say">${esc(actionText)}</textarea>`,
      (item.actions || []).length && !actionText
        ? "This rule has an existing non-speech action. Leave blank to preserve it."
        : "A manual run queues this message through NoorBrain's real TTS service."
    )}

    ${checkbox(
      "nbafEnabled",
      item.enabled !== false
    )}

    <div class="nbaf-info">
      New Smart Rules use a manual schedule and require
      a real action. Failed TTS or device execution is
      reported as a failed run.
    </div>
  `;
}

function sceneFields(item={}) {
  const action=(item.actions || [])[0] || {};

  return `
    ${field(
      "Scene name",
      input("nbafName",item.name,"text",true)
    )}

    ${field(
      "Description",
      `<textarea id="nbafDescription">${esc(
        item.description || ""
      )}</textarea>`
    )}

    ${field(
      "Device",
      `<select id="nbafDevice">
        ${deviceOptions(action.device_id)}
      </select>`,
      devices.length
        ? "Select the device controlled by this scene."
        : "Add a smart-home device before creating a device scene."
    )}

    ${field(
      "Action",
      `<select id="nbafDeviceAction">
        <option value="device_on"
          ${action.type==="device_on" ? "selected" : ""}
        >Turn On</option>
        <option value="device_off"
          ${action.type==="device_off" ? "selected" : ""}
        >Turn Off</option>
        <option value="device_toggle"
          ${action.type==="device_toggle" ? "selected" : ""}
        >Toggle</option>
      </select>`
    )}

    ${checkbox(
      "nbafEnabled",
      item.enabled !== false
    )}
  `;
}

function groupFields(item={}) {
  const selected=(item.device_ids || [])[0] || "";

  return `
    ${field(
      "Group name",
      input("nbafName",item.name,"text",true)
    )}

    ${field(
      "Room",
      input(
        "nbafRoom",
        item.room || "Unassigned"
      )
    )}

    ${field(
      "Device",
      `<select id="nbafDevice">
        ${deviceOptions(selected)}
      </select>`,
      devices.length
        ? "Initial device for this group."
        : "No devices are currently configured."
    )}
  `;
}

function routineFields(item={}) {
  return `
    ${field(
      "Routine name",
      input("nbafName",item.name,"text",true)
    )}

    ${field(
      "Scene",
      `<select id="nbafScene" required>
        ${sceneOptions(item.scene_id)}
      </select>`,
      "A routine runs a Scene."
    )}

    ${field(
      "Time",
      input(
        "nbafSchedule",
        item.schedule || "07:00",
        "time",
        true
      )
    )}

    ${field(
      "Days",
      `<div class="nbaf-days">
        ${[
          "Mon","Tue","Wed","Thu",
          "Fri","Sat","Sun"
        ].map(day => `
          <label>
            <input
              type="checkbox"
              name="nbafDay"
              value="${day}"
              ${
                (item.days || []).includes(day)
                ? "checked"
                : ""
              }
            >
            <span>${day}</span>
          </label>
        `).join("")}
      </div>`
    )}

    ${checkbox(
      "nbafEnabled",
      item.enabled !== false
    )}
  `;
}

async function loadDevices() {
  try {
    const data=await api(API.devices);
    devices=data.devices || [];
  } catch {
    devices=[];
  }
}

async function open(tab,item=null) {
  createSheet();
  await loadDevices();

  if (tab === "reminders") {
    close();

    if (window.NoorMobileRulesV12?.open) {
      await window.NoorMobileRulesV12.open(
        item?.id || "new"
      );
      return;
    }

    const button=document.querySelector(
      '[data-page="reminder-rules"]'
    );

    if (button) {
      button.click();
    } else {
      location.hash="reminder-rules";
    }

    return;
  }

  editing={
    tab,
    item:item || null
  };

  const edit=Boolean(item);

  $("nbafTitle").textContent=
    `${edit ? "Edit" : "Add"} ${
      {
        smart:"Smart Rule",
        scenes:"Scene",
        groups:"Device Group",
        routines:"Routine"
      }[tab] || "Automation"
    }`;

  let html="";

  if (tab==="smart")
    html=smartFields(item || {});

  if (tab==="scenes")
    html=sceneFields(item || {});

  if (tab==="groups")
    html=groupFields(item || {});

  if (tab==="routines")
    html=routineFields(item || {});

  $("nbafFields").innerHTML=html;
  $("nbafMessage").textContent="";

  $("nbAutomationFormV12").hidden=false;
}

function close() {
  const root=$("nbAutomationFormV12");

  if (root)
    root.hidden=true;

  editing=null;
}

function val(id) {
  return $(id)?.value?.trim() || "";
}

function checked(id) {
  return Boolean($(id)?.checked);
}

function payload() {
  const {tab}=editing;

  if (tab==="smart") {
    const actionText=val("nbafActionText");
    let actions=editing.item?.actions || [];

    if(actionText){
      actions=[{
        kind:"halo",
        name:"speak",
        arguments:{text:actionText}
      }];
    }

    if(!actions.length){
      throw new Error(
        "Add a HALO speech action before saving this rule."
      );
    }

    return {
      name:val("nbafName"),
      description:val("nbafDescription"),
      condition_mode:val("nbafConditionMode") || "all",
      conditions:
        editing.item?.conditions || [],
      schedule:
        editing.item?.schedule ||
        {kind:"manual"},
      actions,
      metadata:
        editing.item?.metadata || {},
      enabled:checked("nbafEnabled")
    };
  }

  if (tab==="scenes") {
    const device=val("nbafDevice");

    if (!device)
      throw new Error(
        "No smart-home device is configured yet."
      );

    return {
      name:val("nbafName"),
      description:val("nbafDescription"),
      enabled:checked("nbafEnabled"),
      actions:[{
        type:val("nbafDeviceAction"),
        device_id:device
      }]
    };
  }

  if (tab==="groups") {
    const device=val("nbafDevice");

    return {
      name:val("nbafName"),
      room:val("nbafRoom") || "Unassigned",
      device_ids:device ? [device] : []
    };
  }

  if (tab==="routines") {
    const scene=val("nbafScene");

    if (!scene)
      throw new Error(
        "Create a Scene before creating a Routine."
      );

    return {
      name:val("nbafName"),
      scene_id:scene,
      schedule:val("nbafSchedule"),
      enabled:checked("nbafEnabled"),
      days:[
        ...document.querySelectorAll(
          'input[name="nbafDay"]:checked'
        )
      ].map(x => x.value)
    };
  }

  throw new Error("Unsupported form.");
}

async function save(event) {
  event.preventDefault();

  if (!editing) return;

  const button=$("nbafSave");
  const message=$("nbafMessage");

  try {
    const body=payload();

    button.disabled=true;
    button.textContent="Saving…";
    message.textContent="";

    const base=API[editing.tab];

    const url=editing.item
      ? `${base}/${editing.item.id}`
      : base;

    await api(url,{
      method:editing.item ? "PATCH" : "POST",
      body:JSON.stringify(body)
    });

    close();

    await window.NoorAutomationCenterV12
      ?.load?.();

  } catch (e) {
    message.textContent=e.message;
  } finally {
    button.disabled=false;
    button.textContent="Save";
  }
}

document.addEventListener(
  "noorbrain:automation-add",
  event => {
    open(event.detail?.tab || "smart");
  }
);

document.addEventListener(
  "noorbrain:automation-edit",
  event => {
    open(
      event.detail?.tab || "smart",
      event.detail?.item || null
    );
  }
);

createSheet();

window.NoorAutomationFormsV12={
  version:"12.3.1",
  open,
  close
};

console.log(
  "NOOR_AUTOMATION_FORMS_V12_READY"
);

})();
