const $ = (id) => document.getElementById(id);
async function api(path, options={}) { const response = await fetch(path, options); if (!response.ok) throw new Error(`${response.status} ${response.statusText}`); return response.json(); }
function stat(label, value){ return `<div class="stat"><span class="muted">${label}</span><strong>${value}</strong></div>`; }
async function load(){
  try { const health=await api('/api/ai/health'); $('health').textContent=health.status==='healthy'?'Local AI healthy':'AI issue'; }
  catch(e){ $('health').textContent='Offline'; }
  try { const data=await api('/api/ai/insights'); $('insights').innerHTML=stat('Active memories',data.total_active_memories)+stat('Assistant requests',data.assistant_requests)+stat('Top kind',data.top_kinds?.[0]?.[0]||'—')+stat('Top zone',data.top_zones?.[0]?.[0]||'—'); }
  catch(e){ $('insights').textContent=e.message; }
  try { const data=await api('/api/ai/release'); $('release').innerHTML=stat('Version',data.version)+stat('Cloud required',data.cloud_required?'Yes':'No')+stat('Components',data.components.length); }
  catch(e){ $('release').textContent=e.message; }
}
async function ask(){ const message=$('question').value.trim(); if(!message)return; $('answer').textContent='Thinking locally…'; try { const data=await api('/api/ai/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,limit:8})}); $('answer').textContent=data.answer; } catch(e){ $('answer').textContent=e.message; } }
$('ask').addEventListener('click',ask); $('question').addEventListener('keydown',(event)=>{if(event.key==='Enter')ask();}); load();
