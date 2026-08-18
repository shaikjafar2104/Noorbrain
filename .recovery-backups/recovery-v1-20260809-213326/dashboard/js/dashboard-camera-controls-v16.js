(() => {
  "use strict";

  if (window.NoorBrainDashboardCamera?.installed) return;

  const state = {
    mode: "clean",
    fallbackUsed: false,
    recording: false,
    recorder: null,
    chunks: [],
    canvas: null,
    drawTimer: 0,
  };

  const node = id => document.getElementById(id);
  const feed = () => state.mode === "vision" ? "/vision_feed" : "/camera_feed";

  function modeText(message) {
    const element = node("nbDashboardCameraMode");
    if (element) element.textContent = message;
  }

  function updateOverlayButton() {
    const button = node("nbDashboardCameraOverlay");
    if (button) button.textContent = state.mode === "vision" ? "◉ Overlays On" : "◉ Overlays Off";
  }

  function load() {
    const image = node("nbDashboardCamera");
    if (!image) return;
    image.onload = () => modeText(state.mode === "vision" ? "Vision overlays on" : "Clean Raspberry Pi camera view");
    image.onerror = () => {
      if (state.mode === "clean" && !state.fallbackUsed) {
        state.fallbackUsed = true;
        state.mode = "vision";
        updateOverlayButton();
        modeText("Clean feed unavailable; using Vision feed");
        window.setTimeout(load, 400);
        return;
      }
      modeText("Camera stream unavailable");
      window.setTimeout(load, 1800);
    };
    image.src = `${feed()}?studio=dashboard&v=${Date.now()}`;
  }

  function toggleOverlay() {
    state.mode = state.mode === "vision" ? "clean" : "vision";
    state.fallbackUsed = false;
    updateOverlayButton();
    load();
  }

  function snapshot() {
    const image = node("nbDashboardCamera");
    if (!image?.naturalWidth) { modeText("Camera frame is not ready"); return; }
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(blob => {
      if (!blob) return;
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `noorbrain-dashboard-snapshot-${Date.now()}.jpg`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 5000);
      modeText("Snapshot saved");
    }, "image/jpeg", .92);
  }

  function drawRecording() {
    if (!state.recording || !state.canvas) return;
    const image = node("nbDashboardCamera");
    if (image?.naturalWidth) {
      state.canvas.getContext("2d").drawImage(image, 0, 0, state.canvas.width, state.canvas.height);
    }
    state.drawTimer = requestAnimationFrame(drawRecording);
  }

  function toggleRecording() {
    if (state.recording) {
      if (state.recorder?.state !== "inactive") state.recorder?.stop();
      return;
    }

    const image = node("nbDashboardCamera");
    if (!image?.naturalWidth || !window.MediaRecorder) { modeText("Recording unavailable"); return; }
    state.canvas = document.createElement("canvas");
    state.canvas.width = image.naturalWidth;
    state.canvas.height = image.naturalHeight;
    const stream = state.canvas.captureStream?.(10);
    if (!stream) { modeText("Recording unavailable"); return; }
    const mime = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"]
      .find(type => MediaRecorder.isTypeSupported(type));
    state.recorder = mime ? new MediaRecorder(stream, {mimeType: mime}) : new MediaRecorder(stream);
    state.chunks = [];
    state.recorder.ondataavailable = event => { if (event.data?.size) state.chunks.push(event.data); };
    state.recorder.onstop = () => {
      state.recording = false;
      cancelAnimationFrame(state.drawTimer);
      const blob = new Blob(state.chunks, {type: state.recorder.mimeType || "video/webm"});
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `noorbrain-dashboard-recording-${Date.now()}.webm`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 5000);
      const button = node("nbDashboardCameraRecord");
      button.textContent = "● Record";
      button.classList.remove("is-recording");
      modeText("Recording saved");
    };
    state.recording = true;
    state.recorder.start(500);
    const button = node("nbDashboardCameraRecord");
    button.textContent = "■ Stop";
    button.classList.add("is-recording");
    modeText("Recording camera locally…");
    drawRecording();
  }

  function start() {
    if (!node("nbDashboardCamera")) return;
    node("nbDashboardCameraRefresh").onclick = load;
    node("nbDashboardCameraSnapshot").onclick = snapshot;
    node("nbDashboardCameraFullscreen").onclick = async () => {
      const frame = node("nbDashboardCameraFrame");
      document.fullscreenElement ? await document.exitFullscreen() : await frame.requestFullscreen?.();
    };
    node("nbDashboardCameraRecord").onclick = toggleRecording;
    node("nbDashboardCameraOverlay").onclick = toggleOverlay;
    updateOverlayButton();
    load();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();

  window.NoorBrainDashboardCamera = Object.freeze({installed: true, version: "16.2.0", refresh: load, toggleOverlay});
})();
