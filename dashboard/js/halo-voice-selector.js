(() => {
  if (window.NoorBrainHaloVoiceSelector) return;
  const API="/api/halo-voice-settings";
  const state={voices:[],settings:{voice_name:"",voice_lang:"",rate:1,pitch:1,volume:1,enabled:true}};
  const $=id=>document.getElementById(id);

  async function req(path,options={}) {
    const r=await fetch(path,{headers:{"Content-Type":"application/json"},cache:"no-store",...options});
    const d=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(d.detail||`HTTP ${r.status}`);
    return d;
  }

  function loadVoices(){
    state.voices=(speechSynthesis.getVoices()||[]).slice().sort((a,b)=>a.name.localeCompare(b.name));
    const s=$("nbVoiceSelector");
    if(!s) return;
    s.innerHTML=state.voices.map(v=>`<option value="${encodeURIComponent(v.name)}|||${encodeURIComponent(v.lang)}">${v.name} (${v.lang})</option>`).join("");
    const key=encodeURIComponent(state.settings.voice_name)+"|||"+encodeURIComponent(state.settings.voice_lang);
    if([...s.options].some(o=>o.value===key)) s.value=key;
  }

  function selectedVoice(){
    return state.voices.find(v=>v.name===state.settings.voice_name&&(!state.settings.voice_lang||v.lang===state.settings.voice_lang))
      || state.voices.find(v=>v.lang===state.settings.voice_lang)
      || state.voices[0] || null;
  }

  function speak(text){
    if(!text||!state.settings.enabled||!window.speechSynthesis) return;
    speechSynthesis.cancel();
    const u=new SpeechSynthesisUtterance(String(text));
    const v=selectedVoice();
    if(v){u.voice=v;u.lang=v.lang;}
    u.rate=Number(state.settings.rate||1);
    u.pitch=Number(state.settings.pitch||1);
    u.volume=Number(state.settings.volume??1);
    speechSynthesis.speak(u);
  }

  function pull(){
    const parts=decodeURIComponent($("nbVoiceSelector")?.value||"").split("|||");
    state.settings.voice_name=parts[0]||"";
    state.settings.voice_lang=parts[1]||"";
    state.settings.rate=Number($("nbVoiceRate").value);
    state.settings.pitch=Number($("nbVoicePitch").value);
    state.settings.volume=Number($("nbVoiceVolume").value);
    state.settings.enabled=$("nbVoiceEnabled").checked;
  }

  function labels(){
    $("nbVoiceRateValue").textContent=Number($("nbVoiceRate").value).toFixed(2);
    $("nbVoicePitchValue").textContent=Number($("nbVoicePitch").value).toFixed(2);
    $("nbVoiceVolumeValue").textContent=Math.round(Number($("nbVoiceVolume").value)*100)+"%";
  }

  async function save(){pull();const d=await req(API,{method:"POST",body:JSON.stringify(state.settings)});state.settings=d.settings;$("nbVoiceStatus").textContent="Saved.";}
  async function load(){const d=await req(API);state.settings={...state.settings,...d.settings};$("nbVoiceRate").value=state.settings.rate;$("nbVoicePitch").value=state.settings.pitch;$("nbVoiceVolume").value=state.settings.volume;$("nbVoiceEnabled").checked=state.settings.enabled;loadVoices();labels();}

  function mount(){
    if($("nbVoicePanel")) return;
    const p=document.createElement("section");
    p.id="nbVoicePanel";p.className="nb-voice-panel";
    p.innerHTML=`<div class="nb-voice-head"><div><b>HALO Voice Settings</b><p>Choose voice, speed, pitch and volume.</p></div><label><input id="nbVoiceEnabled" type="checkbox" checked> Voice replies</label></div>
    <label>Voice<select id="nbVoiceSelector"></select></label>
    <div class="nb-voice-grid">
      <label>Speed<input id="nbVoiceRate" type="range" min=".5" max="2" step=".05" value="1"><span id="nbVoiceRateValue">1.00</span></label>
      <label>Pitch<input id="nbVoicePitch" type="range" min=".5" max="2" step=".05" value="1"><span id="nbVoicePitchValue">1.00</span></label>
      <label>Volume<input id="nbVoiceVolume" type="range" min="0" max="1" step=".05" value="1"><span id="nbVoiceVolumeValue">100%</span></label>
    </div>
    <div class="nb-voice-actions"><button id="nbVoiceTest">Test Voice</button><button id="nbVoiceSave">Save Voice</button></div><p id="nbVoiceStatus"></p>`;
    const target=document.querySelector(".nb-halo-oneclick,.nb-halo-card,main,.main,body");
    target===document.body?target.prepend(p):target.insertAdjacentElement("afterend",p);
    ["nbVoiceRate","nbVoicePitch","nbVoiceVolume"].forEach(id=>$(id).addEventListener("input",labels));
    $("nbVoiceTest").onclick=()=>{pull();speak("Assalamu Alaikum. This is the selected HALO voice.");};
    $("nbVoiceSave").onclick=()=>save().catch(e=>$("nbVoiceStatus").textContent=e.message);
    load().catch(e=>$("nbVoiceStatus").textContent=e.message);
  }

  const obs={observe(){}};
  speechSynthesis.onvoiceschanged=loadVoices;
  window.NoorBrainHaloVoiceSelector={speak,loadVoices,save,version:"1.0.0"};
})();
