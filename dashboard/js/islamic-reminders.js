(() => {
  "use strict";
  const API="/api/islamic-reminders";
  const $=id=>document.getElementById(id);

  async function api(path,options={}){
    const response=await fetch(API+path,{
      cache:"no-store",
      headers:{"Content-Type":"application/json"},
      ...options
    });
    const body=await response.json();
    if(!response.ok) throw new Error(body.detail||`HTTP ${response.status}`);
    return body;
  }

  function host(){
    return document.getElementById("page-reminder-rules")
      ||document.getElementById("page-reminders")
      ||document.querySelector("main.main")
      ||document.querySelector("main");
  }

  function ensurePanel(){
    const target=host();
    if(!target) return false;

    if(!$("islamicReminderPanel")){
      const panel=document.createElement("section");
      panel.id="islamicReminderPanel";
      panel.className="card";
      panel.innerHTML=`
        <div class="card-head">
          <div>
            <h2>Islamic Reminder Intelligence</h2>
            <p>Zone, activity, Azkar and family-personalized reminders</p>
          </div>
          <button id="islamicReminderRefresh" class="button secondary">Refresh</button>
        </div>

        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">
          <input id="islamicReminderZone" value="Kitchen" placeholder="Zone">
          <select id="islamicReminderEvent">
            <option value="person_entered">Person entered</option>
            <option value="person_exited">Person exited</option>
            <option value="time">Time trigger</option>
          </select>
          <button id="islamicReminderEvaluate" class="button secondary">Evaluate</button>
          <button id="islamicReminderTrigger" class="button success">Trigger</button>
        </div>

        <div id="islamicReminderSummary">Loading…</div>
        <pre id="islamicReminderResult">Ready</pre>
        <div id="islamicReminderMappings">No mappings.</div>
      `;
      target.appendChild(panel);

      $("islamicReminderRefresh")?.addEventListener("click",load);
      $("islamicReminderEvaluate")?.addEventListener("click",()=>run(false));
      $("islamicReminderTrigger")?.addEventListener("click",()=>run(true));
    }
    return true;
  }

  async function run(trigger){
    const payload={
      event_type:$("islamicReminderEvent")?.value||"person_entered",
      zone:$("islamicReminderZone")?.value?.trim()||null
    };

    const result=await api(trigger?"/trigger":"/evaluate",{
      method:"POST",
      body:JSON.stringify(payload)
    });

    $("islamicReminderResult").textContent=JSON.stringify(result,null,2);
    await load();
  }

  async function load(){
    try{
      const [health,mappings]=await Promise.all([
        api("/health"),
        api("/mappings")
      ]);

      $("islamicReminderSummary").textContent=
        `${health.mapping_count} mappings · ${health.event_count} events`;

      $("islamicReminderMappings").innerHTML=mappings.mappings?.length
        ?mappings.mappings.map(item=>`
          <div style="padding:9px 0;border-bottom:1px solid rgba(255,255,255,.07)">
            <strong>${item.name}</strong><br>
            <small>${item.trigger?.event_type||"any"} · ${item.trigger?.zone||item.trigger?.time_window||"any"} · ${item.enabled?"Enabled":"Disabled"}</small>
          </div>
        `).join("")
        :"No mappings.";
    }catch(error){
      $("islamicReminderSummary").textContent=`Unavailable: ${error.message}`;
    }
  }

  function mount(){
    const ready=ensurePanel();
    if(ready) load();
    return ready;
  }

  if(!mount()){
    const observer=new MutationObserver(()=>{
      if(mount()) observer.disconnect();
    });
    observer.observe(document.documentElement,{childList:true,subtree:true});
    setTimeout(()=>observer.disconnect(),20000);
  }

  window.NoorBrainIslamicReminders={mount,refresh:load};
})();
