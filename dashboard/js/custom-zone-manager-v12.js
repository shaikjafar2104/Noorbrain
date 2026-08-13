(()=>{
"use strict";

const API="/api/vision-zones/zones";

const esc=(v)=>String(v??"")
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

  let d={};

  try{
    d=await r.json();
  }catch{}

  if(!r.ok){
    let msg=d?.detail;

    if(typeof msg==="object"){
      msg=msg.message||
          JSON.stringify(msg);
    }

    throw new Error(
      msg||
      `HTTP ${r.status}`
    );
  }

  return d;
}

function pct(v){
  return Math.round(
    Number(v||0)*100
  );
}

function pointsFromInputs(){
  const x1=Number(
    document.getElementById(
      "nbzX1"
    ).value
  )/100;

  const y1=Number(
    document.getElementById(
      "nbzY1"
    ).value
  )/100;

  const x2=Number(
    document.getElementById(
      "nbzX2"
    ).value
  )/100;

  const y2=Number(
    document.getElementById(
      "nbzY2"
    ).value
  )/100;

  if(
    ![x1,y1,x2,y2]
      .every(
        n=>Number.isFinite(n)
        && n>=0
        && n<=1
      )
  ){
    throw new Error(
      "Area values must be 0–100."
    );
  }

  if(x2<=x1 || y2<=y1){
    throw new Error(
      "Right/Bottom must be larger."
    );
  }

  return [
    {x:x1,y:y1},
    {x:x2,y:y1},
    {x:x2,y:y2},
    {x:x1,y:y2}
  ];
}

function ensure(){
  if(
    document.getElementById(
      "nbZoneManagerV12"
    )
  ) return;

  const button=
    document.createElement("button");

  button.id="nbZoneManagerButtonV12";
  button.textContent="Zones";
  button.type="button";

  button.onclick=()=>open();

  document.body.appendChild(button);

  const modal=
    document.createElement("div");

  modal.id="nbZoneManagerV12";

  modal.innerHTML=`
    <div class="nbz-backdrop"></div>

    <section class="nbz-card">
      <header class="nbz-head">
        <div>
          <strong>Custom Zones</strong>
          <small>
            Camera rooms & reminder areas
          </small>
        </div>

        <button
          id="nbzClose"
          type="button"
        >×</button>
      </header>

      <div class="nbz-create">
        <input
          id="nbzName"
          placeholder="Zone name — e.g. Bedroom"
          maxlength="120"
        >

        <div class="nbz-area">
          <label>
            Left %
            <input
              id="nbzX1"
              type="number"
              min="0"
              max="100"
              value="0"
            >
          </label>

          <label>
            Top %
            <input
              id="nbzY1"
              type="number"
              min="0"
              max="100"
              value="0"
            >
          </label>

          <label>
            Right %
            <input
              id="nbzX2"
              type="number"
              min="0"
              max="100"
              value="100"
            >
          </label>

          <label>
            Bottom %
            <input
              id="nbzY2"
              type="number"
              min="0"
              max="100"
              value="100"
            >
          </label>
        </div>

        <button
          id="nbzAdd"
          class="nbz-primary"
          type="button"
        >
          + Add Zone
        </button>

        <p class="nbz-hint">
          0–100 values represent the camera image.
          Example: left half = 0,0,50,100.
        </p>
      </div>

      <div
        id="nbzStatus"
        class="nbz-status"
      ></div>

      <div
        id="nbzList"
        class="nbz-list"
      ></div>
    </section>
  `;

  document.body.appendChild(modal);

  modal.querySelector(
    ".nbz-backdrop"
  ).onclick=close;

  document.getElementById(
    "nbzClose"
  ).onclick=close;

  document.getElementById(
    "nbzAdd"
  ).onclick=add;
}

function close(){
  document.getElementById(
    "nbZoneManagerV12"
  )?.classList.remove("open");
}

function status(text,error=false){
  const el=document.getElementById(
    "nbzStatus"
  );

  if(!el)return;

  el.textContent=text||"";
  el.classList.toggle(
    "error",
    !!error
  );
}

async function load(){
  const list=document.getElementById(
    "nbzList"
  );

  list.innerHTML=
    `<div class="nbz-loading">
      Loading zones…
    </div>`;

  try{
    const d=await request(API);
    const zones=d.zones||[];

    if(!zones.length){
      list.innerHTML=
        `<div class="nbz-empty">
          No zones yet.
        </div>`;
      return;
    }

    list.innerHTML=zones.map(z=>{
      const p=z.points||[];

      const xs=p.map(x=>x.x);
      const ys=p.map(x=>x.y);

      const left=pct(
        Math.min(...xs)
      );

      const top=pct(
        Math.min(...ys)
      );

      const right=pct(
        Math.max(...xs)
      );

      const bottom=pct(
        Math.max(...ys)
      );

      return `
        <article
          class="nbz-row"
          data-id="${esc(z.id)}"
        >
          <div class="nbz-info">
            <strong>
              ${esc(z.name)}
            </strong>

            <span>
              ${z.enabled
                ?"Enabled"
                :"Disabled"}
              · ${left},${top}
              → ${right},${bottom}%
            </span>
          </div>

          <div class="nbz-actions">
            <button
              data-action="rename"
              type="button"
            >Rename</button>

            <button
              data-action="toggle"
              type="button"
            >
              ${z.enabled
                ?"Disable"
                :"Enable"}
            </button>

            <button
              data-action="delete"
              class="danger"
              type="button"
            >Delete</button>
          </div>
        </article>
      `;
    }).join("");

    list.querySelectorAll(
      "[data-action]"
    ).forEach(btn=>{
      btn.onclick=()=>action(
        btn.closest(".nbz-row")
          .dataset.id,
        btn.dataset.action,
        zones
      );
    });

  }catch(e){
    list.innerHTML="";
    status(e.message,true);
  }
}

async function add(){
  try{
    status("Saving…");

    const name=
      document.getElementById(
        "nbzName"
      ).value.trim();

    if(!name){
      throw new Error(
        "Enter a zone name."
      );
    }

    const points=
      pointsFromInputs();

    await request(API,{
      method:"POST",
      body:JSON.stringify({
        name,
        camera_id:"primary",
        points,
        enabled:true,
        metadata:{
          frame_width:1280,
          frame_height:720,
          source:
            "custom-zone-manager-v12.5"
        }
      })
    });

    document.getElementById(
      "nbzName"
    ).value="";

    status(
      `Zone "${name}" created.`
    );

    await load();

  }catch(e){
    status(e.message,true);
  }
}

async function action(id,type,zones){
  const z=zones.find(
    x=>x.id===id
  );

  if(!z)return;

  try{
    if(type==="rename"){
      const name=prompt(
        "New zone name:",
        z.name
      );

      if(name===null)return;

      if(!name.trim()){
        throw new Error(
          "Zone name cannot be empty."
        );
      }

      status(
        "Renaming zone and linked rules…"
      );

      const d=await request(
        `${API}/${encodeURIComponent(id)}`,
        {
          method:"PUT",
          body:JSON.stringify({
            name:name.trim()
          })
        }
      );

      status(
        `Renamed. Linked rules updated: ${
          d.renamed_rules||0
        }`
      );
    }

    if(type==="toggle"){
      await request(
        `${API}/${encodeURIComponent(id)}`,
        {
          method:"PUT",
          body:JSON.stringify({
            enabled:!z.enabled
          })
        }
      );

      status(
        !z.enabled
          ?"Zone enabled."
          :"Zone disabled."
      );
    }

    if(type==="delete"){
      if(
        !confirm(
          `Delete zone "${z.name}"?`
        )
      ) return;

      await request(
        `${API}/${encodeURIComponent(id)}`,
        {
          method:"DELETE"
        }
      );

      status("Zone deleted.");
    }

    await load();

  }catch(e){
    status(e.message,true);

    if(
      type==="delete" &&
      String(e.message)
        .includes("linked reminder")
    ){
      alert(
        "This zone is used by Reminder Rules.\n\n"+
        "Rename the zone instead, or remove/reassign "+
        "its reminder rules before deleting it."
      );
    }
  }
}

async function open(){
  ensure();

  document.getElementById(
    "nbZoneManagerV12"
  ).classList.add("open");

  status("");
  await load();
}

window.NoorZoneManagerV12={
  open,
  load
};

if(
  document.readyState==="loading"
){
  document.addEventListener(
    "DOMContentLoaded",
    ensure
  );
}else{
  ensure();
}

console.log(
  "NOOR_CUSTOM_ZONE_MANAGER_V12_READY"
);
})();
