(()=>{
"use strict";

const API={
  zones:"/api/vision-zones/zones",
  media:"/api/media",
  rules:"/reminder-rules"
};

let state={
  zones:[],
  media:[],
  rules:[]
};

const $=id=>document.getElementById(id);

const esc=v=>String(v??"")
  .replaceAll("&","&amp;")
  .replaceAll("<","&lt;")
  .replaceAll(">","&gt;")
  .replaceAll('"',"&quot;");

async function request(url,opt={}){
  const r=await fetch(url,{
    cache:"no-store",
    ...opt,
    headers:{
      "Content-Type":"application/json",
      ...(opt.headers||{})
    }
  });

  let data={};

  try{
    data=await r.json();
  }catch{}

  if(!r.ok){
    let msg=data?.detail;

    if(typeof msg==="object"){
      msg=msg.message||JSON.stringify(msg);
    }

    throw new Error(msg||`HTTP ${r.status}`);
  }

  return data;
}

function ensure(){
  if($("nbIslamicRuleCreatorV12")) return;

  const modal=document.createElement("div");
  modal.id="nbIslamicRuleCreatorV12";

  modal.innerHTML=`
    <div class="nbirc-backdrop"></div>

    <section class="nbirc-card">

      <header class="nbirc-head">
        <div>
          <strong>Islamic Smart Rule</strong>
          <small>
            Activity → Zone → Islamic Audio
          </small>
        </div>

        <button id="nbircClose" type="button">×</button>
      </header>

      <div class="nbirc-grid">

        <label>
          Zone
          <select id="nbircZone"></select>
        </label>

        <label>
          Activity
          <select id="nbircTrigger">
            <option value="entered_zone">Entered Zone</option>
            <option value="left_zone">Left Zone</option>
            <option value="stayed">Stayed in Zone</option>
            <option value="appeared">Person Appeared</option>
            <option value="disappeared">Person Disappeared</option>
          </select>
        </label>

        <label class="nbirc-wide">
          Islamic Audio
          <select id="nbircMedia"></select>
        </label>

        <label>
          Cooldown
          <select id="nbircCooldown">
            <option value="300">5 minutes</option>
            <option value="900">15 minutes</option>
            <option value="1800">30 minutes</option>
            <option value="3600" selected>1 hour</option>
            <option value="7200">2 hours</option>
            <option value="21600">6 hours</option>
            <option value="43200">12 hours</option>
            <option value="86400">24 hours</option>
          </select>
        </label>

        <label class="nbirc-enabled">
          <input id="nbircEnabled" type="checkbox" checked>
          Rule enabled
        </label>

        <label class="nbirc-wide">
          Rule Name
          <input
            id="nbircName"
            maxlength="120"
            placeholder="Example: Bedroom – Dua Before Sleeping"
          >
        </label>

        <button
          id="nbircSave"
          class="nbirc-primary nbirc-wide"
          type="button"
        >
          Create Smart Rule
        </button>

      </div>

      <div id="nbircStatus" class="nbirc-status"></div>

      <div class="nbirc-title">
        <strong>Active Rules</strong>
        <button id="nbircRefresh" type="button">Refresh</button>
      </div>

      <div id="nbircRules"></div>

    </section>
  `;

  document.body.appendChild(modal);

  modal.querySelector(".nbirc-backdrop").onclick=close;
  $("nbircClose").onclick=close;
  $("nbircRefresh").onclick=load;
  $("nbircSave").onclick=createRule;

  $("nbircZone").onchange=autoName;
  $("nbircMedia").onchange=autoName;
}

function status(text,error=false){
  const el=$("nbircStatus");
  if(!el) return;

  el.textContent=text||"";
  el.classList.toggle("error",error);
}

function close(){
  $("nbIslamicRuleCreatorV12")?.classList.remove("open");
}

function mediaName(m){
  return String(
    m?.name ||
    m?.title ||
    m?.original_filename ||
    m?.stored_filename ||
    "Islamic Audio"
  );
}

function autoName(){
  const zone=$("nbircZone")?.value||"";
  const mediaId=$("nbircMedia")?.value||"";

  const media=state.media.find(
    m=>String(m.id)===String(mediaId)
  );

  if(zone && media){
    $("nbircName").value=
      `${zone} – ${mediaName(media)}`;
  }
}

function renderSelectors(){
  const zones=state.zones.filter(
    z=>z.enabled!==false
  );

  $("nbircZone").innerHTML=
    zones.length
    ? zones.map(z=>`
        <option value="${esc(z.name)}">
          ${esc(z.name)}
        </option>
      `).join("")
    : `<option value="">No zones available</option>`;

  $("nbircMedia").innerHTML=
    state.media.length
    ? state.media.map(m=>`
        <option value="${esc(m.id)}">
          ${esc(mediaName(m))}
        </option>
      `).join("")
    : `<option value="">No Islamic audio available</option>`;

  autoName();
}

function renderRules(){
  const root=$("nbircRules");

  if(!state.rules.length){
    root.innerHTML=
      `<div class="nbirc-empty">No rules configured.</div>`;
    return;
  }

  root.innerHTML=state.rules.map(r=>`
    <article class="nbirc-rule">

      <div>
        <strong>${esc(r.name)}</strong>

        <span>
          ${esc(r.zone||"Any zone")}
          · ${esc(r.trigger)}
          · ${Math.round(Number(r.cooldown_seconds||0)/60)} min
        </span>
      </div>

      <b>
        ${r.enabled===false ? "Off" : "On"}
      </b>

    </article>
  `).join("");
}

async function load(){
  try{
    status("Loading…");

    const [zones,media,rules]=await Promise.all([
      request(API.zones),
      request(API.media),
      request(API.rules)
    ]);

    state.zones=zones.zones||[];
    state.media=media.items||[];
    state.rules=rules.rules||[];

    renderSelectors();
    renderRules();

    status(
      `${state.zones.length} zones · `+
      `${state.media.length} Islamic audios · `+
      `${state.rules.length} rules`
    );

  }catch(err){
    status(err.message,true);
  }
}

async function createRule(){
  try{
    const zone=$("nbircZone").value;
    const trigger=$("nbircTrigger").value;
    const mediaId=$("nbircMedia").value;
    const cooldown=Number($("nbircCooldown").value);
    const enabled=$("nbircEnabled").checked;
    const name=$("nbircName").value.trim();

    if(!zone) throw new Error("Select a zone.");
    if(!mediaId) throw new Error("Select Islamic audio.");
    if(!name) throw new Error("Enter a rule name.");

    const media=state.media.find(
      m=>String(m.id)===String(mediaId)
    );

    if(!media){
      throw new Error("Selected audio was not found.");
    }

    const duplicate=state.rules.find(r=>
      r.zone===zone &&
      r.trigger===trigger &&
      String(r.media_id)===String(mediaId)
    );

    if(duplicate){
      throw new Error(
        `This rule already exists: ${duplicate.name}`
      );
    }

    status("Creating rule…");

    await request(API.rules,{
      method:"POST",
      body:JSON.stringify({
        name,
        enabled,
        trigger,
        zone,
        message:mediaName(media),
        cooldown_seconds:cooldown,
        speak:false,
        media_id:mediaId
      })
    });

    await load();

    status(`Created: ${name}`);

  }catch(err){
    status(err.message,true);
  }
}

async function open(){
  ensure();

  $("nbIslamicRuleCreatorV12").classList.add("open");

  await load();
}

window.NoorIslamicRuleCreatorV12={
  open,
  load
};

if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",ensure);
}else{
  ensure();
}

console.log("NOOR_ISLAMIC_RULE_CREATOR_V12_READY");
})();
