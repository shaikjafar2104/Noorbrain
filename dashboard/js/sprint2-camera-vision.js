(() => {
  "use strict";

  if (window.NoorBrainSprint2Vision) return;

  const VERSION = "2.0.0";
  const STORE_KEY = "noorbrain.sprint2.cameras";

  const state = {
    cameras: [],
    active: null,
    frame: {width: 1280, height: 720},
    detections: [],
    zones: [],
    overlay: true,
    pollTimer: null,
    drawTimer: null,
    recording: false,
    mediaRecorder: null,
    recordChunks: [],
    recordCanvas: null,
    recordContext: null,
  };

  const $ = id => document.getElementById(id);

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function json(path, options = {}) {
    const response = await fetch(path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    const body = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(body.detail || body.message || `HTTP ${response.status}`);
    }

    return body;
  }

  function loadSavedCameras() {
    let saved = [];

    try {
      saved = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
    } catch (_) {}

    const defaults = [
      {id: "primary", name: "Primary Camera", stream_url: "/vision_feed"},
    ];

    state.cameras = [...defaults];

    for (const camera of saved) {
      if (
        camera
        && camera.id
        && camera.stream_url
        && !state.cameras.some(item => item.id === camera.id)
      ) {
        state.cameras.push(camera);
      }
    }

    state.active = state.cameras[0];
  }

  function saveCameras() {
    localStorage.setItem(
      STORE_KEY,
      JSON.stringify(
        state.cameras.filter(camera => camera.id !== "primary")
      )
    );
  }

  function streamUrl(camera) {
    const url = camera?.stream_url || "/vision_feed";
    return `${url}${url.includes("?") ? "&" : "?"}v=${Date.now()}`;
  }

  function mount() {
    const cameraSection =
      document.querySelector(".nbv2-camera-section")
      || document.querySelector("#nbv2CameraSection")
      || document.querySelector("main");

    if (!cameraSection || $("nbs2VisionProduct")) return;

    const panel = document.createElement("section");
    panel.id = "nbs2VisionProduct";
    panel.className = "nbs2-panel";

    panel.innerHTML = `
      <article class="nbs2-card">
        <div class="nbs2-head">
          <div>
            <small>SPRINT 2</small>
            <h2>Camera & Vision Product</h2>
          </div>
          <div class="nbs2-head-actions">
            <button class="nbs2-button" id="nbs2Reconnect">Reconnect</button>
            <button class="nbs2-button primary" id="nbs2AddCamera">＋ Camera</button>
          </div>
        </div>

        <div class="nbs2-view" id="nbs2View">
          <img id="nbs2Feed" alt="NoorBrain live camera">
          <canvas id="nbs2Overlay"></canvas>
          <span class="nbs2-live" id="nbs2Live"><i></i> LIVE</span>
          <span class="nbs2-camera-name" id="nbs2CameraName">Primary Camera</span>
        </div>

        <div class="nbs2-camera-tabs" id="nbs2CameraTabs"></div>

        <div class="nbs2-toolbar">
          <button class="nbs2-button" id="nbs2Snapshot">◉ Snapshot</button>
          <button class="nbs2-button" id="nbs2Fullscreen">⛶ Full Screen</button>
          <button class="nbs2-button" id="nbs2Record">● Record</button>
          <button class="nbs2-button" id="nbs2OverlayToggle">👁 Overlay ON</button>
          <button class="nbs2-button" id="nbs2VisionRestart">↻ Vision</button>
          <button class="nbs2-button" id="nbs2OpenStudio">⚙ Studio</button>
        </div>

        <div class="nbs2-metrics">
          <div class="nbs2-metric"><span>People</span><b id="nbs2People">0</b></div>
          <div class="nbs2-metric"><span>Zones</span><b id="nbs2Zones">0</b></div>
          <div class="nbs2-metric"><span>Camera</span><b id="nbs2CameraHealth">Checking</b></div>
          <div class="nbs2-metric"><span>Vision</span><b id="nbs2VisionHealth">Checking</b></div>
        </div>

        <p class="nbs2-notice" id="nbs2Notice">Loading live vision state…</p>
      </article>

      <article class="nbs2-card">
        <div class="nbs2-head">
          <div>
            <small>INTELLIGENCE</small>
            <h2>Detections & Zones</h2>
          </div>
          <div class="nbs2-head-actions">
            <button class="nbs2-button" id="nbs2Refresh">Refresh</button>
          </div>
        </div>

        <div class="nbs2-settings">
          <label>
            Overlay refresh
            <select id="nbs2PollRate">
              <option value="500">0.5 seconds</option>
              <option value="1000" selected>1 second</option>
              <option value="2000">2 seconds</option>
            </select>
          </label>

          <label>
            Camera fit
            <select id="nbs2Fit">
              <option value="contain" selected>Contain</option>
              <option value="cover">Cover</option>
            </select>
          </label>
        </div>

        <div class="nbs2-list" id="nbs2DetectionList">
          <div class="nbs2-row">No detections.</div>
        </div>
      </article>
    `;

    cameraSection.insertAdjacentElement("afterend", panel);

    bind();
    renderCameraTabs();
    selectCamera(state.active?.id || "primary");
    startPolling();
  }

  function bind() {
    $("nbs2Snapshot").onclick = snapshot;
    $("nbs2Fullscreen").onclick = fullscreen;
    $("nbs2Record").onclick = toggleRecording;
    $("nbs2OverlayToggle").onclick = toggleOverlay;
    $("nbs2VisionRestart").onclick = restartVision;
    $("nbs2Reconnect").onclick = reconnectCamera;
    $("nbs2OpenStudio").onclick = () => location.href = "/studio#vision";
    $("nbs2AddCamera").onclick = addCamera;
    $("nbs2Refresh").onclick = refreshState;
    $("nbs2PollRate").onchange = startPolling;
    $("nbs2Fit").onchange = event => {
      $("nbs2Feed").style.objectFit = event.target.value;
    };

    window.addEventListener("resize", resizeOverlay);
    $("nbs2Feed").addEventListener("load", resizeOverlay);
  }

  function renderCameraTabs() {
    const host = $("nbs2CameraTabs");

    host.innerHTML = state.cameras.map(camera => `
      <button
        class="nbs2-camera-tab ${camera.id === state.active?.id ? "active" : ""}"
        data-camera="${safe(camera.id)}"
      >
        ${safe(camera.name)}
      </button>
    `).join("");

    host.querySelectorAll("[data-camera]").forEach(button => {
      button.onclick = () => selectCamera(button.dataset.camera);
    });
  }

  function selectCamera(cameraId) {
    const camera = state.cameras.find(item => item.id === cameraId);
    if (!camera) return;

    state.active = camera;
    $("nbs2CameraName").textContent = camera.name;
    $("nbs2Feed").src = streamUrl(camera);
    renderCameraTabs();
  }

  function addCamera() {
    const name = prompt("Camera name:", "Camera 2");
    if (!name) return;

    const stream = prompt(
      "MJPEG stream URL:",
      "http://RASPBERRY_PI_IP:8000/vision_feed"
    );

    if (!stream) return;

    const camera = {
      id: `camera-${Date.now()}`,
      name: name.trim(),
      stream_url: stream.trim(),
    };

    state.cameras.push(camera);
    saveCameras();
    renderCameraTabs();
    selectCamera(camera.id);
  }

  function resizeOverlay() {
    const image = $("nbs2Feed");
    const canvas = $("nbs2Overlay");
    const rect = image.getBoundingClientRect();

    canvas.width = Math.max(1, Math.round(rect.width));
    canvas.height = Math.max(1, Math.round(rect.height));
    drawOverlay();
  }

  function bbox(person) {
    const value =
      person.bbox
      || person.box
      || person.bounding_box
      || person.xyxy
      || null;

    if (Array.isArray(value) && value.length >= 4) {
      return {
        x1: Number(value[0]),
        y1: Number(value[1]),
        x2: Number(value[2]),
        y2: Number(value[3]),
      };
    }

    if (value && typeof value === "object") {
      const x = Number(value.x ?? value.left ?? value.x1 ?? 0);
      const y = Number(value.y ?? value.top ?? value.y1 ?? 0);
      const w = Number(value.w ?? value.width ?? 0);
      const h = Number(value.h ?? value.height ?? 0);

      return {
        x1: x,
        y1: y,
        x2: Number(value.x2 ?? value.right ?? x + w),
        y2: Number(value.y2 ?? value.bottom ?? y + h),
      };
    }

    return null;
  }

  function zonePoints(zone) {
    const points = zone.points || zone.polygon || zone.coordinates || [];
    if (!Array.isArray(points)) return [];

    return points.map(point => {
      if (Array.isArray(point)) {
        return {x: Number(point[0]), y: Number(point[1])};
      }

      return {
        x: Number(point.x ?? 0),
        y: Number(point.y ?? 0),
      };
    });
  }

  function toCanvasX(value, canvas) {
    const numeric = Number(value);
    return numeric <= 1
      ? numeric * canvas.width
      : numeric * canvas.width / state.frame.width;
  }

  function toCanvasY(value, canvas) {
    const numeric = Number(value);
    return numeric <= 1
      ? numeric * canvas.height
      : numeric * canvas.height / state.frame.height;
  }

  function drawOverlay() {
    const canvas = $("nbs2Overlay");
    if (!canvas) return;

    const context = canvas.getContext("2d");
    context.clearRect(0, 0, canvas.width, canvas.height);

    if (!state.overlay) return;

    context.lineWidth = 2;
    context.font = "12px sans-serif";

    state.zones.forEach(zone => {
      const points = zonePoints(zone);
      if (points.length < 2) return;

      context.beginPath();
      points.forEach((point, index) => {
        const x = toCanvasX(point.x, canvas);
        const y = toCanvasY(point.y, canvas);

        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });

      context.closePath();
      context.strokeStyle = "rgba(99,119,255,.95)";
      context.fillStyle = "rgba(99,119,255,.11)";
      context.fill();
      context.stroke();

      const first = points[0];
      context.fillStyle = "#cbd5ff";
      context.fillText(
        String(zone.name || "Zone"),
        toCanvasX(first.x, canvas) + 4,
        toCanvasY(first.y, canvas) + 14
      );
    });

    state.detections.forEach((person, index) => {
      const box = bbox(person);
      if (!box) return;

      const x1 = toCanvasX(box.x1, canvas);
      const y1 = toCanvasY(box.y1, canvas);
      const x2 = toCanvasX(box.x2, canvas);
      const y2 = toCanvasY(box.y2, canvas);

      context.strokeStyle = "rgba(66,224,173,.98)";
      context.fillStyle = "rgba(66,224,173,.14)";
      context.strokeRect(x1, y1, x2 - x1, y2 - y1);
      context.fillRect(x1, y1, x2 - x1, y2 - y1);

      context.fillStyle = "#d9fff3";
      context.fillText(
        String(person.name || person.label || `Person ${index + 1}`),
        x1 + 4,
        Math.max(12, y1 - 5)
      );
    });
  }

  async function refreshState() {
    try {
      const [stats, detections, zones, size] = await Promise.all([
        json("/camera/stats"),
        json("/detections"),
        json("/zones"),
        json("/frame_size"),
      ]);

      state.detections = detections.people || [];
      state.zones = zones.zones || [];
      state.frame = {
        width: Number(size.width || 1280),
        height: Number(size.height || 720),
      };

      $("nbs2People").textContent = detections.count ?? state.detections.length;
      $("nbs2Zones").textContent = zones.count ?? state.zones.length;
      $("nbs2CameraHealth").textContent =
        stats.camera?.connected === false ? "Offline" : "Online";
      $("nbs2VisionHealth").textContent =
        stats.vision?.running === false ? "Stopped" : "Running";

      $("nbs2Notice").textContent =
        `${state.detections.length} people · ${state.zones.length} zones · ${state.frame.width}×${state.frame.height}`;

      renderDetectionList();
      resizeOverlay();
    } catch (error) {
      $("nbs2Notice").textContent = `Vision refresh failed: ${error.message}`;
    }
  }

  function renderDetectionList() {
    const host = $("nbs2DetectionList");

    if (!state.detections.length) {
      host.innerHTML = '<div class="nbs2-row">No people detected.</div>';
      return;
    }

    host.innerHTML = state.detections.map((person, index) => `
      <div class="nbs2-row">
        <strong>${safe(person.name || person.label || `Person ${index + 1}`)}</strong>
        <small>
          ${safe(person.zone || person.zone_name || "No zone")} ·
          confidence ${safe(person.confidence ?? person.score ?? "—")}
        </small>
      </div>
    `).join("");
  }

  function startPolling() {
    clearInterval(state.pollTimer);

    const delay = Number($("nbs2PollRate")?.value || 1000);
    refreshState();

    state.pollTimer = setInterval(refreshState, delay);
  }

  function toggleOverlay() {
    state.overlay = !state.overlay;
    $("nbs2OverlayToggle").textContent =
      state.overlay ? "👁 Overlay ON" : "👁 Overlay OFF";
    drawOverlay();
  }

  async function reconnectCamera() {
    try {
      await json("/control/camera/reconnect", {
        method: "POST",
        body: "{}",
      });

      $("nbs2Notice").textContent = "Camera reconnect requested.";
      selectCamera(state.active?.id || "primary");
    } catch (error) {
      $("nbs2Notice").textContent = `Reconnect failed: ${error.message}`;
    }
  }

  async function restartVision() {
    try {
      await json("/control/vision/restart", {
        method: "POST",
        body: "{}",
      });

      $("nbs2Notice").textContent = "Vision restarted.";
      await refreshState();
    } catch (error) {
      $("nbs2Notice").textContent = `Vision restart failed: ${error.message}`;
    }
  }

  async function fullscreen() {
    const view = $("nbs2View");

    if (document.fullscreenElement) {
      await document.exitFullscreen?.();
    } else {
      await view.requestFullscreen?.();
    }
  }

  function snapshot() {
    const image = $("nbs2Feed");
    const canvas = document.createElement("canvas");

    canvas.width = image.naturalWidth || state.frame.width;
    canvas.height = image.naturalHeight || state.frame.height;

    const context = canvas.getContext("2d");

    try {
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const link = document.createElement("a");
      link.download = `noorbrain-snapshot-${Date.now()}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
      $("nbs2Notice").textContent = "Snapshot saved.";
    } catch (_) {
      window.open(image.src, "_blank", "noopener");
    }
  }

  function prepareRecordingCanvas() {
    const image = $("nbs2Feed");
    const canvas = document.createElement("canvas");

    canvas.width = image.naturalWidth || state.frame.width;
    canvas.height = image.naturalHeight || state.frame.height;

    state.recordCanvas = canvas;
    state.recordContext = canvas.getContext("2d");

    const render = () => {
      if (!state.recording) return;

      try {
        state.recordContext.drawImage(
          image,
          0,
          0,
          canvas.width,
          canvas.height
        );
      } catch (_) {}

      state.drawTimer = requestAnimationFrame(render);
    };

    render();
    return canvas;
  }

  function toggleRecording() {
    if (state.recording) {
      state.mediaRecorder?.stop();
      return;
    }

    const canvas = prepareRecordingCanvas();
    const stream = canvas.captureStream?.(10);

    if (!stream || !window.MediaRecorder) {
      state.recording = false;
      cancelAnimationFrame(state.drawTimer);
      $("nbs2Notice").textContent =
        "Recording is unavailable in this browser.";
      return;
    }

    const mime = [
      "video/webm;codecs=vp9",
      "video/webm;codecs=vp8",
      "video/webm",
    ].find(type => MediaRecorder.isTypeSupported(type));

    state.recordChunks = [];
    state.mediaRecorder = mime
      ? new MediaRecorder(stream, {mimeType: mime})
      : new MediaRecorder(stream);

    state.mediaRecorder.ondataavailable = event => {
      if (event.data?.size) state.recordChunks.push(event.data);
    };

    state.mediaRecorder.onstop = () => {
      state.recording = false;
      cancelAnimationFrame(state.drawTimer);

      const blob = new Blob(state.recordChunks, {
        type: state.mediaRecorder.mimeType || "video/webm",
      });

      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `noorbrain-recording-${Date.now()}.webm`;
      link.click();

      setTimeout(() => URL.revokeObjectURL(link.href), 5000);

      $("nbs2Record").textContent = "● Record";
      $("nbs2Record").classList.remove("nbs2-recording");
      $("nbs2Notice").textContent = "Recording saved.";
    };

    state.mediaRecorder.start(500);
    state.recording = true;

    $("nbs2Record").textContent = "■ Stop";
    $("nbs2Record").classList.add("nbs2-recording");
    $("nbs2Notice").textContent = "Recording camera locally…";
  }

  loadSavedCameras();

  window.NoorBrainSprint2Vision = {
    version: VERSION,
    refresh: refreshState,
    reconnect: reconnectCamera,
    restartVision,
    snapshot,
    toggleRecording,
    selectCamera,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
