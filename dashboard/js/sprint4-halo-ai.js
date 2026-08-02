(() => {
  "use strict";

  if (window.NoorBrainSprint4HALO) return;

  const API = "/api/halo-ai-v4";

  const state = {
    recording: false,
    recorder: null,
    stream: null,
    chunks: [],
    profile: {
      name: "Home",
      language: "auto",
      wake_phrase: "halo",
      voice_enabled: true,
    },
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
    const halo =
      document.querySelector(".nbv2-halo-section")
      || document.querySelector("#nbv2Halo")
      || document.querySelector("main");

    if (!halo || $("nbs4HALO")) return;

    const panel = document.createElement("section");
    panel.id = "nbs4HALO";
    panel.className = "nbs4-panel";

    panel.innerHTML = `
      <article class="nbs4-card">
        <div class="nbs4-head">
          <div>
            <small>SPRINT 4</small>
            <h2>HALO AI</h2>
          </div>
          <div class="nbs4-actions">
            <button class="nbs4-button" id="nbs4Clear">Clear</button>
            <button class="nbs4-button" id="nbs4OpenStudio">Studio</button>
          </div>
        </div>

        <div class="nbs4-chat" id="nbs4Chat"></div>

        <div class="nbs4-compose">
          <textarea id="nbs4Input" placeholder="Ask HALO anything…"></textarea>
          <button class="nbs4-orb" id="nbs4Mic" title="Push to talk">🎤</button>
          <button class="nbs4-button primary" id="nbs4Send">Send</button>
        </div>

        <div class="nbs4-intent">
          <article><span>Intent</span><b id="nbs4Intent">—</b></article>
          <article><span>Confidence</span><b id="nbs4Confidence">—</b></article>
          <article><span>Profile</span><b id="nbs4ProfileName">Home</b></article>
        </div>

        <p class="nbs4-status" id="nbs4Status">HALO ready.</p>
      </article>

      <article class="nbs4-card">
        <div class="nbs4-head">
          <div>
            <small>VOICE & MEMORY</small>
            <h2>Assistant Settings</h2>
          </div>
          <div class="nbs4-actions">
            <button class="nbs4-button primary" id="nbs4SaveProfile">Save</button>
          </div>
        </div>

        <div class="nbs4-settings">
          <label>
            Profile name
            <input id="nbs4ProfileInput" value="Home">
          </label>

          <label>
            Language
            <select id="nbs4Language">
              <option value="auto">Auto</option>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="ur">Urdu</option>
              <option value="ar">Arabic</option>
            </select>
          </label>

          <label>
            Wake phrase
            <input id="nbs4WakePhrase" value="halo">
          </label>

          <label>
            Voice replies
            <select id="nbs4VoiceEnabled">
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
          </label>
        </div>
      </article>
    `;

    halo.insertAdjacentElement("afterend", panel);

    bind();
    Promise.allSettled([
      loadMemory(),
      loadProfile(),
    ]);
  }

  function bind() {
    $("nbs4Send").onclick = () => send();
    $("nbs4Mic").onclick = toggleMic;
    $("nbs4Clear").onclick = clearMemory;
    $("nbs4OpenStudio").onclick = () => location.href = "/studio#halo";
    $("nbs4SaveProfile").onclick = saveProfile;

    $("nbs4Input").addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        send();
      }
    });
  }

  function appendMessage(role, text, meta = {}) {
    const host = $("nbs4Chat");

    const node = document.createElement("div");
    node.className = `nbs4-message ${role}`;
    node.innerHTML = `
      ${safe(text)}
      <small>${safe(meta.label || (role === "user" ? "You" : "HALO"))}</small>
    `;

    host.appendChild(node);
    host.scrollTop = host.scrollHeight;
  }

  async function loadMemory() {
    try {
      const data = await request(`${API}/memory?limit=50`);

      $("nbs4Chat").innerHTML = "";

      for (const message of data.messages) {
        appendMessage(
          message.role === "user" ? "user" : "assistant",
          message.text,
          {label: message.role === "user" ? "You" : "HALO"}
        );
      }

      if (!data.messages.length) {
        appendMessage(
          "assistant",
          "Assalamu Alaikum. HALO is ready.",
          {label: "HALO"}
        );
      }
    } catch (error) {
      $("nbs4Status").textContent = error.message;
    }
  }

  async function send(text = "") {
    const input = $("nbs4Input");
    const message = String(text || input.value || "").trim();

    if (!message) return;

    input.value = "";
    appendMessage("user", message);
    $("nbs4Status").textContent = "Understanding command…";

    try {
      const intent = await request(`${API}/intent`, {
        method: "POST",
        body: JSON.stringify({text: message}),
      });

      $("nbs4Intent").textContent = intent.intent;
      $("nbs4Confidence").textContent =
        `${Math.round(Number(intent.confidence || 0) * 100)}%`;

      await execute(message, intent);
    } catch (error) {
      $("nbs4Status").textContent = error.message;
      appendMessage("assistant", `Error: ${error.message}`);
    }
  }

  async function execute(message, intent) {
    let reply = "";

    if (intent.intent === "device_control") {
      reply = await controlDevice(intent.entities);
    } else if (intent.intent === "open_module") {
      reply = openModule(intent.entities.target);
    } else {
      reply = await askHALO(message);
    }

    appendMessage("assistant", reply);
    $("nbs4Status").textContent = "Ready.";

    if (state.profile.voice_enabled) {
      window.NoorBrainHALOSpeak?.(reply);
    }
  }

  async function askHALO(message) {
    try {
      const oneClick = await request("/api/halo-oneclick/command", {
        method: "POST",
        body: JSON.stringify({message}),
      });

      if (oneClick.status !== "forward") {
        return oneClick.reply || "Done.";
      }
    } catch (_) {}

    const response = await request("/halo", {
      method: "POST",
      body: JSON.stringify({message}),
    });

    return response.reply || response.message || "Done.";
  }

  async function controlDevice(entities) {
    const wanted = String(entities.device || "").trim().toLowerCase();
    const requestedState = String(entities.state || "").toLowerCase();

    const home = await request("/api/smart-home-v3/state");

    const device = home.home.devices.find(item =>
      String(item.name || "").toLowerCase().includes(wanted)
    );

    if (!device) {
      return `I could not find ${entities.device}.`;
    }

    const result = await request(
      `/api/smart-home-v3/devices/${device.id}/state`,
      {
        method: "POST",
        body: JSON.stringify({state: requestedState}),
      }
    );

    return `${result.device.name} is ${result.device.state}.`;
  }

  function openModule(target) {
    const routes = {
      camera: "/mobile#camera",
      vision: "/studio#vision",
      devices: "/mobile#devices",
      prayer: "/studio#prayer-intelligence",
      automation: "/studio#smart-automation",
      reminders: "/studio#islamic-reminders",
    };

    const route = routes[target] || "/studio";
    setTimeout(() => location.href = route, 500);

    return `Opening ${target}.`;
  }

  async function toggleMic() {
    if (state.recording) {
      state.recorder.stop();
      return;
    }

    if (!window.isSecureContext) {
      $("nbs4Status").textContent = "Microphone requires HTTPS or localhost.";
      return;
    }

    try {
      state.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const mime = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
      ].find(type => MediaRecorder.isTypeSupported(type));

      state.recorder = mime
        ? new MediaRecorder(state.stream, {mimeType: mime})
        : new MediaRecorder(state.stream);

      state.chunks = [];
      state.recording = true;
      $("nbs4Mic").textContent = "■";
      $("nbs4Mic").classList.add("recording");
      $("nbs4Status").textContent = "Listening… tap Stop when finished.";

      state.recorder.ondataavailable = event => {
        if (event.data?.size) state.chunks.push(event.data);
      };

      state.recorder.onstop = async () => {
        state.recording = false;
        state.stream.getTracks().forEach(track => track.stop());
        $("nbs4Mic").textContent = "🎤";
        $("nbs4Mic").classList.remove("recording");
        $("nbs4Status").textContent = "Transcribing locally…";

        const form = new FormData();
        form.append(
          "audio",
          new Blob(state.chunks, {
            type: state.recorder.mimeType || "audio/webm",
          }),
          "halo-v4.webm"
        );

        try {
          const response = await fetch("/api/halo-voice/transcribe", {
            method: "POST",
            body: form,
          });

          const data = await response.json().catch(() => ({}));

          if (!response.ok) {
            throw new Error(data.detail || `Voice HTTP ${response.status}`);
          }

          await send(data.command || data.text);
        } catch (error) {
          $("nbs4Status").textContent = error.message;
        }
      };

      state.recorder.start(250);
    } catch (error) {
      $("nbs4Status").textContent = error.message;
    }
  }

  async function clearMemory() {
    await request(`${API}/memory`, {
      method: "DELETE",
    });

    $("nbs4Chat").innerHTML = "";
    appendMessage(
      "assistant",
      "Conversation memory cleared.",
      {label: "HALO"}
    );
  }

  async function loadProfile() {
    try {
      const data = await request(`${API}/profiles`);
      const profile =
        data.profiles[data.active_profile]
        || data.profiles.default;

      state.profile = profile;
      $("nbs4ProfileName").textContent = profile.name || "Home";
      $("nbs4ProfileInput").value = profile.name || "Home";
      $("nbs4Language").value = profile.language || "auto";
      $("nbs4WakePhrase").value = profile.wake_phrase || "halo";
      $("nbs4VoiceEnabled").value =
        String(profile.voice_enabled !== false);
    } catch (error) {
      $("nbs4Status").textContent = error.message;
    }
  }

  async function saveProfile() {
    const profile = {
      name: $("nbs4ProfileInput").value.trim() || "Home",
      language: $("nbs4Language").value,
      wake_phrase: $("nbs4WakePhrase").value.trim() || "halo",
      voice_enabled: $("nbs4VoiceEnabled").value === "true",
      activate: true,
    };

    const data = await request(`${API}/profiles/default`, {
      method: "POST",
      body: JSON.stringify(profile),
    });

    state.profile = data.profile;
    $("nbs4ProfileName").textContent = data.profile.name;
    $("nbs4Status").textContent = "HALO profile saved.";
  }

  window.NoorBrainSprint4HALO = {
    version: "4.0.0",
    send,
    toggleMic,
    loadMemory,
    clearMemory,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
