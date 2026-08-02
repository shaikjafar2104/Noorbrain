(() => {
  if (window.NoorBrainHaloVoice) return;
  const state = { recorder:null, stream:null, chunks:[], recording:false };
  const reply = () => document.querySelector('#nbHaloReply');
  const input = () => document.querySelector('#nbHaloInput');
  function notice(text){ const el=reply(); if(el) el.textContent=text; }
  async function send(blob){
    const form=new FormData(); form.append('audio',blob,'halo.webm');
    const r=await fetch('/api/halo-voice/transcribe',{method:'POST',body:form});
    const data=await r.json().catch(()=>({})); if(!r.ok) throw new Error(data.detail||`HTTP ${r.status}`); return data;
  }
  async function start(){
    if(!navigator.mediaDevices?.getUserMedia) throw new Error('Microphone recording unavailable. Use HTTPS or localhost.');
    state.stream=await navigator.mediaDevices.getUserMedia({audio:true});
    const type=['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus'].find(MediaRecorder.isTypeSupported);
    state.chunks=[]; state.recorder=type?new MediaRecorder(state.stream,{mimeType:type}):new MediaRecorder(state.stream);
    state.recorder.ondataavailable=e=>{if(e.data?.size) state.chunks.push(e.data)};
    state.recorder.onstop=async()=>{
      state.recording=false; document.body.classList.remove('nb-local-listening');
      document.querySelector('#nbLocalVoice').textContent='🎤'; state.stream?.getTracks().forEach(t=>t.stop()); notice('Transcribing locally…');
      try{
        const result=await send(new Blob(state.chunks,{type:state.recorder.mimeType||'audio/webm'}));
        if(!result.command){notice(result.text?'Wake phrase not detected.':'No clear speech detected.');return;}
        if(input()) input().value=result.command;
        if(window.NoorBrainHaloOneClick?.sendCommand) await window.NoorBrainHaloOneClick.sendCommand(result.command);
        else notice(result.command);
      }catch(e){notice(e.message)}
    };
    state.recorder.start(); state.recording=true; document.body.classList.add('nb-local-listening');
    document.querySelector('#nbLocalVoice').textContent='■'; notice('Listening locally… tap Stop when finished.');
  }
  function stop(){if(state.recording&&state.recorder) state.recorder.stop()}
  async function toggle(){try{state.recording?stop():await start()}catch(e){notice(e.message)}}
  function mount(){
    const orb=document.querySelector('#nbHaloMic'); if(!orb){setTimeout(mount,700);return}
    if(document.querySelector('#nbLocalVoice')) return;
    const b=document.createElement('button'); b.id='nbLocalVoice'; b.className='nb-local-voice'; b.type='button'; b.title='Offline HALO microphone'; b.textContent='🎤'; b.onclick=toggle; orb.insertAdjacentElement('afterend',b);
  }
  window.NoorBrainHaloVoice={start,stop,toggle};
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',mount):mount();
})();
