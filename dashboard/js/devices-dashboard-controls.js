(() => {
  "use strict";
  const API_BASE = "/api/devices";
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => [...r.querySelectorAll(s)];

  async function api(path="", options={}) {
    const response = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      headers: {"Content-Type":"application/json", "Accept":"application/json", ...(options.headers||{})},
      ...options,
    });
    const raw = await response.text();
    let body;
    try { body = JSON.parse(raw); } catch { body = {detail: raw}; }
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function toast(message, kind="success") {
    let box = $("#nbDeviceToastContainer");
    if (!box) {
      box = document.createElement("div");
      box.id = "nbDeviceToastContainer";
      box.className = "nb-device-toast-container";
      document.body.appendChild(box);
    }
    const item = document.createElement("div");
    item.className = `nb-device-toast is-${kind}`;
    item.textContent = message;
    box.appendChild(item);
    setTimeout(() => item.remove(), 3500);
  }

  function modal() {
    let node = $("#nbDeviceModal");
    if (node) return node;
    node = document.createElement("div");
    node.id = "nbDeviceModal";
    node.className = "nb-device-modal";
    node.hidden = true;
    node.innerHTML = `
      <div class="nb-device-modal__backdrop" data-close-modal></div>
      <div class="nb-device-modal__panel" role="dialog" aria-modal="true">
        <div class="nb-device-modal__header">
          <h3 id="nbDeviceModalTitle">Add Device</h3>
          <button type="button" class="nb-device-icon-button" data-close-modal>×</button>
        </div>
        <form id="nbDeviceForm" class="nb-device-form">
          <input type="hidden" id="nbDeviceId">
          <label><span>Name</span><input id="nbDeviceName" required maxlength="120"></label>
          <label><span>Type</span><select id="nbDeviceType" required>
            <option value="light">Light</option><option value="fan">Fan</option>
            <option value="plug">Plug</option><option value="relay">Relay</option>
            <option value="switch">Switch</option><option value="sensor">Sensor</option>
            <option value="motion_sensor">Motion sensor</option><option value="door_sensor">Door sensor</option>
            <option value="temperature_sensor">Temperature sensor</option><option value="humidity_sensor">Humidity sensor</option>
            <option value="camera">Camera</option><option value="other">Other</option>
          </select></label>
          <label><span>Room</span><input id="nbDeviceRoom" required maxlength="120" value="Unassigned"></label>
          <label><span>State</span><select id="nbDeviceState"><option value="unknown">Unknown</option><option value="off">Off</option><option value="on">On</option></select></label>
          <label><span>IP address</span><input id="nbDeviceIp" maxlength="64" placeholder="192.168.2.50"></label>
          <label><span>Manufacturer</span><input id="nbDeviceManufacturer" maxlength="120"></label>
          <label><span>Model</span><input id="nbDeviceModel" maxlength="120"></label>
          <label class="nb-device-checkbox"><input type="checkbox" id="nbDeviceOnline"><span>Device is online</span></label>
          <div class="nb-device-form__actions">
            <button type="button" class="nb-device-button is-secondary" data-close-modal>Cancel</button>
            <button type="submit" class="nb-device-button is-primary" id="nbDeviceSaveButton">Save Device</button>
          </div>
        </form>
      </div>`;
    document.body.appendChild(node);
    $$('[data-close-modal]', node).forEach(b => b.addEventListener('click', closeModal));
    $("#nbDeviceForm", node).addEventListener("submit", saveDevice);
    return node;
  }

  function closeModal(){ const m=$("#nbDeviceModal"); if(m) m.hidden=true; }
  function currentDevices(){ return window.NoorDevicesDashboard?.devices || []; }
  function currentDevice(id){ return currentDevices().find(d => d.id===id) || null; }

  function openModal(device=null){
    const m=modal(); m.hidden=false;
    $("#nbDeviceModalTitle").textContent = device ? "Edit Device" : "Add Device";
    $("#nbDeviceId").value = device?.id || "";
    $("#nbDeviceName").value = device?.name || "";
    $("#nbDeviceType").value = device?.device_type || "light";
    $("#nbDeviceRoom").value = device?.room || "Unassigned";
    $("#nbDeviceState").value = device?.state || "unknown";
    $("#nbDeviceIp").value = device?.ip_address || "";
    $("#nbDeviceManufacturer").value = device?.manufacturer || "";
    $("#nbDeviceModel").value = device?.model || "";
    $("#nbDeviceOnline").checked = Boolean(device?.online);
    $("#nbDeviceName").focus();
  }

  function payload(){
    return {
      name: $("#nbDeviceName").value.trim(),
      device_type: $("#nbDeviceType").value,
      room: $("#nbDeviceRoom").value.trim() || "Unassigned",
      state: $("#nbDeviceState").value,
      online: $("#nbDeviceOnline").checked,
      ip_address: $("#nbDeviceIp").value.trim() || null,
      manufacturer: $("#nbDeviceManufacturer").value.trim() || null,
      model: $("#nbDeviceModel").value.trim() || null,
      metadata: {},
    };
  }

  async function refresh(){ await window.NoorDevicesDashboard?.refresh?.(); setTimeout(enhance, 50); }

  async function saveDevice(event){
    event.preventDefault();
    const id=$("#nbDeviceId").value.trim();
    const button=$("#nbDeviceSaveButton"); button.disabled=true; button.textContent="Saving…";
    try {
      if(id){ await api(`/${id}`, {method:"PATCH", body:JSON.stringify(payload())}); toast("Device updated."); }
      else { await api("", {method:"POST", body:JSON.stringify(payload())}); toast("Device added."); }
      closeModal(); await refresh();
    } catch(error){ toast(error.message || String(error), "error"); }
    finally { button.disabled=false; button.textContent="Save Device"; }
  }

  async function control(id, action){
    try { await api(`/${id}/${action}`, {method:"POST"}); toast(`Device ${action} completed.`); await refresh(); }
    catch(error){ toast(error.message || String(error), "error"); }
  }

  async function removeDevice(id){
    const device=currentDevice(id); if(!confirm(`Delete "${device?.name || id}"?`)) return;
    try { await api(`/${id}`, {method:"DELETE"}); toast("Device deleted."); await refresh(); }
    catch(error){ toast(error.message || String(error), "error"); }
  }

  function addToolbar(){
    const section=$("#nbDevicesSection"); if(!section || $("#nbDevicesToolbar", section)) return;
    const top=$(".nb-devices-top", section); if(!top) return;
    const bar=document.createElement("div"); bar.id="nbDevicesToolbar"; bar.className="nb-devices-toolbar";
    bar.innerHTML='<button class="nb-device-button is-secondary" id="nbDevicesRefreshButton">Refresh</button><button class="nb-device-button is-primary" id="nbDevicesAddButton">+ Add Device</button>';
    top.appendChild(bar);
    $("#nbDevicesRefreshButton").addEventListener("click", refresh);
    $("#nbDevicesAddButton").addEventListener("click", () => openModal());
  }

  function actions(id){
    const node=document.createElement("div"); node.className="nb-device-actions";
    node.innerHTML='<button class="nb-device-action" data-a="toggle">Toggle</button><button class="nb-device-action" data-a="on">On</button><button class="nb-device-action" data-a="off">Off</button><button class="nb-device-action" data-a="edit">Edit</button><button class="nb-device-action is-danger" data-a="delete">Delete</button>';
    $$('[data-a]', node).forEach(button => button.addEventListener('click', async () => {
      const a=button.dataset.a;
      if(a==='edit') return openModal(currentDevice(id));
      if(a==='delete') return removeDevice(id);
      return control(id, a);
    }));
    return node;
  }

  function enhance(){
    addToolbar();
    $$(".nb-device-card").forEach(card => {
      if(card.dataset.controlsReady==='true') return;
      const id=card.dataset.deviceId; if(!id) return;
      card.dataset.controlsReady='true'; card.appendChild(actions(id));
    });
  }

  function mount(){ modal(); new MutationObserver(enhance).observe(document.body,{childList:true,subtree:true}); enhance(); setInterval(enhance,1500); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', mount); else mount();
  window.NoorDeviceControls={openAdd:()=>openModal(), refresh};
})();
