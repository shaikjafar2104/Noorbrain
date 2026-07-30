(() => {
  "use strict";
  if (window.NoorBrainHaloOneClick) return;

  const API = "/api/halo-oneclick";
  const state = { devices: [], recognition: null, listening: false };

  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  })[c]);

  async function json(path, options = {}) {
    const response = await fetch(path, {
      headers: {"Content-Type":"application/json","Accept":"application/json"},
      ...options
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
    return data;
  }

  function toast(message, type="success") {
    let node = document.querySelector(".nb-halo-toast");
    if (!node) {
      node = document.createElement("div");
      node.className = "nb-halo-toast";
      document.body.appendChild(node);
    }
    node.textContent = message;
    node.dataset.type = type;
    node.classList.add("show");
    clearTimeout(node._timer);
    node._timer = setTimeout(() => node.classList.remove("show"), 2800);
  }

  function speak(text) {
    if (!text || !("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    speechSynthesis.speak(utterance);
  }

  async function sendCommand(message) {
    const input = document.querySelector("#nbHaloInput");
    const output = document.querySelector("#nbHaloReply");
    const orb = document.querySelector(".nb-halo-orb");
    message = String(message || input?.value || "").trim();
    if (!message) return;
    if (input) input.value = "";
    output.textContent = "Thinking…";
    orb?.classList.add("thinking");

    try {
      const result = await json(`${API}/command`, {
        method:"POST", body:JSON.stringify({message})
      });
      let reply = result.reply;
      if (result.status === "forward") {
        const halo = await json("/halo", {
          method:"POST", body:JSON.stringify({message})
        });
        reply = halo.reply || halo.message || "Done.";
      }
      output.textContent = reply || "Done.";
      speak(reply);
      await loadDevices();
    } catch (error) {
      output.textContent = error.message;
      toast(error.message, "error");
    } finally {
      orb?.classList.remove("thinking");
    }
  }

  function setupMic() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const mic = document.querySelector("#nbHaloMic");
    if (!mic) return;

    if (!SpeechRecognition) {
      mic.title = "Browser speech recognition unavailable. Text command use karein.";
      mic.classList.add("unsupported");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = navigator.language || "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onstart = () => {
      state.listening = true;
      mic.classList.add("listening");
      document.querySelector("#nbHaloReply").textContent = "Listening…";
    };
    recognition.onend = () => {
      state.listening = false;
      mic.classList.remove("listening");
    };
    recognition.onerror = event => {
      const message = event.error === "not-allowed"
        ? "Microphone permission allow karein. LAN HTTP par Chrome mic block kar sakta hai."
        : `Microphone error: ${event.error}`;
      toast(message, "error");
      document.querySelector("#nbHaloReply").textContent = message;
    };
    recognition.onresult = event => {
      const text = event.results[0][0].transcript;
      document.querySelector("#nbHaloInput").value = text;
      sendCommand(text);
    };
    state.recognition = recognition;

    mic.addEventListener("click", () => {
      try {
        state.listening ? recognition.stop() : recognition.start();
      } catch (_) {}
    });
  }

  function deviceIcon(type) {
    return ({light:"💡", switch:"⏻", speaker:"🔊", camera:"📷",
      thermostat:"🌡️", sensor:"◉", fan:"🌀"})[type] || "⌁";
  }

  function renderDevices() {
    const grid = document.querySelector("#nbDeviceGrid");
    if (!grid) return;
    if (!state.devices.length) {
      grid.innerHTML = `<button class="nb-add-first" id="nbAddFirst">＋ Add your first home device</button>`;
      document.querySelector("#nbAddFirst")?.addEventListener("click", openDeviceModal);
      return;
    }
    grid.innerHTML = state.devices.map(device => `
      <article class="nb-device-card ${device.state === "on" ? "active" : ""}">
        <button class="nb-device-main" data-toggle="${esc(device.id)}">
          <span class="nb-device-icon">${deviceIcon(device.type)}</span>
          <span><b>${esc(device.name)}</b><small>${esc(device.room)} · ${esc(device.type)}</small></span>
          <span class="nb-device-state">${device.state === "on" ? "ON" : "OFF"}</span>
        </button>
        <button class="nb-device-delete" data-delete="${esc(device.id)}" title="Delete">×</button>
      </article>
    `).join("");

    grid.querySelectorAll("[data-toggle]").forEach(button => button.addEventListener("click", async () => {
      try {
        await json(`${API}/devices/${button.dataset.toggle}/toggle`, {method:"POST", body:"{}"});
        await loadDevices();
      } catch (error) { toast(error.message, "error"); }
    }));
    grid.querySelectorAll("[data-delete]").forEach(button => button.addEventListener("click", async event => {
      event.stopPropagation();
      if (!confirm("Delete this device?")) return;
      try {
        await json(`${API}/devices/${button.dataset.delete}`, {method:"DELETE"});
        await loadDevices();
      } catch (error) { toast(error.message, "error"); }
    }));
  }

  async function loadDevices() {
    try {
      const result = await json(`${API}/devices`);
      state.devices = result.devices || [];
      renderDevices();
    } catch (_) {}
  }

  function openDeviceModal() {
    let modal = document.querySelector("#nbDeviceModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "nbDeviceModal";
      modal.className = "nb-modal";
      modal.innerHTML = `
        <form class="nb-modal-card" id="nbDeviceForm">
          <div class="nb-modal-head"><div><h2>Add Home Device</h2><p>One simple form. Advanced connection optional.</p></div><button type="button" data-close>×</button></div>
          <div class="nb-form-grid">
            <label>Device name<input name="name" required placeholder="Hall Light"></label>
            <label>Room<input name="room" value="Hall" placeholder="Hall"></label>
            <label>Type<select name="type"><option value="light">Light</option><option value="switch">Switch</option><option value="speaker">Speaker</option><option value="camera">Camera</option><option value="fan">Fan</option><option value="thermostat">Thermostat</option><option value="sensor">Sensor</option></select></label>
            <label>Connection<select name="protocol" id="nbProtocol"><option value="local">Manual / local foundation</option><option value="http">HTTP smart device</option></select></label>
          </div>
          <details id="nbAdvanced"><summary>Advanced device connection</summary>
            <div class="nb-form-grid">
              <label class="wide">Base URL<input name="base_url" placeholder="http://192.168.1.50"></label>
              <label>ON endpoint<input name="on_endpoint" value="/on"></label>
              <label>OFF endpoint<input name="off_endpoint" value="/off"></label>
              <label>Method<select name="method"><option>POST</option><option>GET</option><option>PUT</option></select></label>
              <label>Token (optional)<input name="token" type="password"></label>
            </div>
          </details>
          <div class="nb-modal-actions"><button type="button" class="secondary" data-close>Cancel</button><button type="submit">Add Device</button></div>
        </form>`;
      document.body.appendChild(modal);
      modal.querySelectorAll("[data-close]").forEach(x => x.addEventListener("click", () => modal.classList.remove("open")));
      modal.addEventListener("click", e => { if (e.target === modal) modal.classList.remove("open"); });
      modal.querySelector("#nbProtocol").addEventListener("change", e => {
        modal.querySelector("#nbAdvanced").open = e.target.value === "http";
      });
      modal.querySelector("#nbDeviceForm").addEventListener("submit", async e => {
        e.preventDefault();
        const payload = Object.fromEntries(new FormData(e.target).entries());
        try {
          await json(`${API}/devices`, {method:"POST", body:JSON.stringify(payload)});
          modal.classList.remove("open");
          e.target.reset();
          toast("Device added.");
          await loadDevices();
        } catch (error) { toast(error.message, "error"); }
      });
    }
    modal.classList.add("open");
  }

  function mount() {
    const host = document.createElement("section");
    host.className = "nb-halo-oneclick";
    host.innerHTML = `
      <div class="nb-halo-card">
        <div class="nb-halo-top">
          <button class="nb-halo-orb" id="nbHaloMic" aria-label="Talk to HALO"><span>✦</span></button>
          <div><span class="nb-eyebrow">HALO ASSISTANT</span><h2>How can I help?</h2><p id="nbHaloReply">Tap the orb or type a command.</p></div>
        </div>
        <div class="nb-command-row"><input id="nbHaloInput" placeholder='Try: "Hall light on karo"'><button id="nbHaloSend">Send</button></div>
        <div class="nb-quick-actions">
          <button data-command="Show my home devices">My devices</button>
          <button data-command="What is the next prayer?">Next prayer</button>
          <button data-command="Open camera status">Camera</button>
          <button data-command="Show my reminders">Reminders</button>
        </div>
      </div>
      <div class="nb-devices-panel">
        <div class="nb-section-title"><div><span class="nb-eyebrow">MY HOME</span><h2>Devices</h2></div><button id="nbAddDevice">＋ Add Device</button></div>
        <div id="nbDeviceGrid" class="nb-device-grid"></div>
      </div>`;

    const target = document.querySelector("main, .main, .content, #content, body");
    if (target === document.body) document.body.prepend(host);
    else target.prepend(host);

    document.querySelector("#nbHaloSend").addEventListener("click", () => sendCommand());
    document.querySelector("#nbHaloInput").addEventListener("keydown", e => {
      if (e.key === "Enter") sendCommand();
    });
    document.querySelectorAll("[data-command]").forEach(button =>
      button.addEventListener("click", () => sendCommand(button.dataset.command)));
    document.querySelector("#nbAddDevice").addEventListener("click", openDeviceModal);

    setupMic();
    loadDevices();
  }

  window.NoorBrainHaloOneClick = {sendCommand, loadDevices, openDeviceModal};
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
