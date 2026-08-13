(() => {
  "use strict";

  const VERSION = "3.1.0";
  const VOICE_API = "/api/halo-voice";
  const NATIVE_START_TIMEOUT_MS = 15000;
  const RECORDING_TIMEOUT_MS = 12000;
  const PROCESSING_TIMEOUT_MS = 45000;
  const state = {
    recorder: null,
    stream: null,
    chunks: [],
    recording: false,
    activeButton: null,
    mode: "idle",
    operation: 0,
    timer: null,
    processing: false,
    nativeTranscriptHandled: false,
    lastTranscript: "",
    lastTranscriptAt: 0,
  };

  function isNativeApp() {
    return new URLSearchParams(location.search)
      .get("native_app") === "1";
  }

  function clearTimer() {
    if (state.timer !== null) {
      window.clearTimeout(state.timer);
      state.timer = null;
    }
  }

  function scheduleTimer(callback, delay) {
    clearTimer();
    const operation = state.operation;
    state.timer = window.setTimeout(() => {
      state.timer = null;
      if (operation === state.operation) callback();
    }, delay);
  }

  function statusNode() {
    return document.querySelector(
      "#nb126HaloStatus, #nbUniversalVoiceStatus, #nbHaloReply, [data-halo-reply]"
    );
  }

  function inputNode() {
    return document.querySelector(
      "#nb126HaloInput, #nbHaloInput, [data-halo-input]"
    );
  }

  function setStatus(message, mode = "") {
    const nodes = document.querySelectorAll(
      "#nb126HaloStatus, #nbUniversalVoiceStatus, #nbHaloReply, [data-halo-reply]"
    );

    nodes.forEach(node => {
      node.textContent = message;
      node.dataset.voiceMode = mode;
    });
  }

  function setButtonsRecording(recording) {
    document.body.classList.toggle(
      "nb-halo-final-recording",
      recording
    );

    document.querySelectorAll(
      "[data-nb-final-mic='true']"
    ).forEach(button => {
      button.setAttribute(
        "aria-pressed",
        String(recording)
      );

      const label = button.querySelector(
        "[data-nb-mic-label]"
      );

      if (label) {
        label.textContent = recording
          ? "Stop"
          : "Talk to HALO";
      }

      const icon = button.querySelector(
        "[data-nb-mic-icon]"
      );

      if (icon) {
        icon.textContent = recording
          ? "■"
          : "🎤";
      }
    });

    document.querySelectorAll(
      ".nb126-orb[data-nb126-action='halo-live']"
    ).forEach(button => {
      button.setAttribute("aria-pressed", String(recording));
      button.dataset.voiceMode = recording ? "listening" : state.mode;
    });

    document.querySelectorAll(".nb126-halo-prompt")
      .forEach(node => {
        node.textContent = recording ? "Tap to stop" : "Tap to talk";
      });
  }

  function setMode(mode, message = "", statusMode = "") {
    state.mode = mode;
    state.recording = mode === "listening";
    setButtonsRecording(state.recording);
    if (message) setStatus(message, statusMode || mode);
  }

  function reset(message = "", mode = "") {
    clearTimer();
    state.operation += 1;
    state.processing = false;
    state.nativeTranscriptHandled = false;
    state.chunks = [];
    state.recorder = null;
    state.stream = null;
    state.activeButton = null;
    setMode("idle", message, mode);
  }

  function fail(error, fallback = "Voice processing failed.") {
    const message = String(error?.message || error || fallback);
    state.stream?.getTracks?.().forEach(track => track.stop());
    reset(message, "error");
    return false;
  }

  function chooseMimeType() {
    if (!window.MediaRecorder) {
      return "";
    }

    return [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ].find(type =>
      MediaRecorder.isTypeSupported(type)
    ) || "";
  }

  async function transcribe(blob) {
    const form = new FormData();
    const type = blob.type || "audio/webm";

    let extension = "webm";
    if (type.includes("ogg")) {
      extension = "ogg";
    } else if (type.includes("mp4")) {
      extension = "m4a";
    }

    form.append(
      "audio",
      blob,
      `halo-final.${extension}`
    );

    const response = await fetch(
      `${VOICE_API}/transcribe`,
      {
        method: "POST",
        body: form,
        cache: "no-store",
      }
    );

    const payload = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        payload.detail
        || `Voice backend HTTP ${response.status}`
      );
    }

    return payload;
  }

  async function sendToHalo(command) {
    const clean = String(command || "").trim();

    if (!clean) {
      throw new Error(
        "No command was detected."
      );
    }

    const input = inputNode();
    if (input) {
      input.value = clean;
    }

    if (
      window.NoorBrainMobile126
      && typeof window.NoorBrainMobile126
        .sendHalo === "function"
    ) {
      await window.NoorBrainMobile126.sendHalo(clean);
      return;
    }

    if (
      window.NoorBrainHaloOneClick
      && typeof window.NoorBrainHaloOneClick
        .sendCommand === "function"
    ) {
      await window.NoorBrainHaloOneClick
        .sendCommand(clean);
      return;
    }

    const response = await fetch(
      "/api/halo-oneclick/command",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-cache",
        },
        body: JSON.stringify({
          message: clean,
        }),
        cache: "no-store",
      }
    );

    const payload = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        payload.detail
        || `HALO HTTP ${response.status}`
      );
    }

    if (payload.status === "forward") {
      const fallback = await fetch(
        "/halo",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: clean,
          }),
          cache: "no-store",
        }
      );

      const halo = await fallback
        .json()
        .catch(() => ({}));

      if (!fallback.ok) {
        throw new Error(
          halo.detail
          || `HALO HTTP ${fallback.status}`
        );
      }

      setStatus(
        halo.reply || halo.message || "Done.",
        "done"
      );
      return;
    }

    setStatus(
      payload.reply || "Done.",
      "done"
    );
  }

  async function startRecording(button) {
    if (state.mode !== "idle") return false;

    state.operation += 1;
    const operation = state.operation;
    state.activeButton = button || null;
    setMode("starting", "Requesting microphone…", "thinking");

    if (!window.isSecureContext) {
      throw new Error(
        "Microphone requires HTTPS or localhost."
      );
    }

    if (
      !navigator.mediaDevices
      || !navigator.mediaDevices.getUserMedia
      || !window.MediaRecorder
    ) {
      throw new Error(
        "This browser cannot record audio."
      );
    }

    const stream = await navigator
      .mediaDevices
      .getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });

    if (operation !== state.operation) {
      stream.getTracks().forEach(track => track.stop());
      return false;
    }

    const mimeType = chooseMimeType();

    const options = mimeType
      ? {
          mimeType,
          audioBitsPerSecond: 64000,
        }
      : undefined;

    const recorder = options
      ? new MediaRecorder(stream, options)
      : new MediaRecorder(stream);

    state.stream = stream;
    state.recorder = recorder;
    state.chunks = [];
    state.activeButton = button;

    recorder.ondataavailable = event => {
      if (event.data && event.data.size > 0) {
        state.chunks.push(event.data);
      }
    };

    recorder.onerror = event => {
      if (operation !== state.operation) return;
      fail(event.error, "Microphone recording failed.");
    };

    recorder.onstop = async () => {
      if (operation !== state.operation || state.processing) return;
      state.processing = true;
      clearTimer();

      state.stream
        ?.getTracks()
        .forEach(track => track.stop());

      setMode(
        "processing",
        "Transcribing on NoorBrain…",
        "thinking"
      );

      scheduleTimer(() => {
        fail("Voice processing timed out. Please try again.");
      }, PROCESSING_TIMEOUT_MS);

      try {
        const blob = new Blob(
          state.chunks,
          {
            type: recorder.mimeType
              || "audio/webm",
          }
        );

        if (blob.size < 1200) {
          throw new Error(
            "Recording too short. Speak for 3–8 seconds."
          );
        }

        const result = await transcribe(blob);

        const command = String(
          result.command || result.text || ""
        ).trim();

        if (operation !== state.operation) return;

        setStatus(
          `Heard: ${result.text}`,
          "heard"
        );

        await sendToHalo(command);
        if (operation === state.operation) reset();
      } catch (error) {
        if (operation === state.operation) fail(error);
      }
    };

    recorder.start(250);
    setMode(
      "listening",
      "Listening… speak for 3–8 seconds, then press Stop.",
      "listening"
    );

    scheduleTimer(() => {
      stopRecording("automatic timeout");
    }, RECORDING_TIMEOUT_MS);

    return true;
  }

  function stopRecording(reason = "second tap") {
    if (
      state.recorder
      && state.recording
      && state.recorder.state !== "inactive"
    ) {
      clearTimer();
      setMode(
        "stopping",
        reason === "automatic timeout"
          ? "Recording limit reached. Processing voice…"
          : "Processing voice…",
        "thinking"
      );
      state.recorder.stop();
      return true;
    }
    return false;
  }

  function postNativeToggle() {
    window.parent.postMessage(
      { type: "noorbrain-native-record-toggle" },
      "*"
    );
  }

  function startNative(button) {
    if (state.mode !== "idle") return false;

    state.operation += 1;
    state.activeButton = button || null;
    state.nativeTranscriptHandled = false;
    setMode("starting", "Starting microphone…", "thinking");
    postNativeToggle();

    scheduleTimer(() => {
      fail("The Android microphone did not start. Tap to try again.");
    }, NATIVE_START_TIMEOUT_MS);
    return true;
  }

  function stopNative(reason = "second tap") {
    if (state.mode !== "listening") return false;

    clearTimer();
    setMode(
      "stopping",
      reason === "automatic timeout"
        ? "Recording limit reached. Processing voice…"
        : "Processing voice…",
      "thinking"
    );
    postNativeToggle();

    scheduleTimer(() => {
      fail("Android voice processing timed out. Tap to try again.");
    }, PROCESSING_TIMEOUT_MS);
    return true;
  }

  async function handleNativeMessage(event) {
    if (!isNativeApp()) return false;
    const data = event?.data || {};

    if (data.type === "noorbrain-native-listening") {
      if (state.mode !== "starting") return false;
      setMode(
        "listening",
        "Listening… tap again when finished.",
        "listening"
      );
      scheduleTimer(() => stopNative("automatic timeout"), RECORDING_TIMEOUT_MS);
      return true;
    }

    if (data.type === "noorbrain-native-processing") {
      if (!["listening", "stopping"].includes(state.mode)) return false;
      clearTimer();
      setMode("processing", "Transcribing on NoorBrain…", "thinking");
      scheduleTimer(() => {
        fail("Android transcription timed out. Tap to try again.");
      }, PROCESSING_TIMEOUT_MS);
      return true;
    }

    if (data.type === "noorbrain-native-error") {
      if (state.mode === "idle") return false;
      fail(data.message || "Android microphone failed.");
      return true;
    }

    if (data.type !== "noorbrain-native-transcript") return false;
    if (state.mode === "idle" || state.nativeTranscriptHandled) return false;

    const text = String(data.text || "").trim();
    const now = Date.now();
    if (text && text === state.lastTranscript && now - state.lastTranscriptAt < 30000) {
      return false;
    }

    state.nativeTranscriptHandled = true;
    state.lastTranscript = text;
    state.lastTranscriptAt = now;
    clearTimer();

    if (!text) {
      fail("No clear speech detected. Please try again.");
      return true;
    }

    const operation = state.operation;
    setMode("conversation", `Heard: ${text}`, "heard");

    try {
      await sendToHalo(text);
      if (operation === state.operation) reset();
    } catch (error) {
      if (operation === state.operation) fail(error, "Noor request failed.");
    }
    return true;
  }

  function toggle(button) {
    if (isNativeApp()) {
      if (state.mode === "listening") return Promise.resolve(stopNative());
      if (state.mode !== "idle") return Promise.resolve(false);
      return Promise.resolve(startNative(button));
    }

    if (state.mode === "listening") {
      stopRecording();
      return Promise.resolve();
    }

    if (state.mode !== "idle") return Promise.resolve(false);

    return startRecording(button).catch(error => {
      return fail(error, "Microphone failed.");
    });
  }

  function replaceButton(oldButton) {
    if (
      !oldButton
      || oldButton.dataset.nbFinalMic === "true"
    ) {
      return oldButton;
    }

    const replacement = oldButton.cloneNode(true);

    replacement.dataset.nbFinalMic = "true";
    replacement.removeAttribute("onclick");
    replacement.title =
      "HALO local voice transcription";

    if (
      replacement.id === "nbHaloMic"
      || replacement.id === "nbUniversalMic"
      || replacement.id === "nbVoiceOfflineMic"
    ) {
      replacement.innerHTML = `
        <span data-nb-mic-icon>🎤</span>
        <b data-nb-mic-label>Talk to HALO</b>
      `;
    }

    oldButton.replaceWith(replacement);

    replacement.addEventListener(
      "click",
      event => {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        toggle(replacement);
      },
      true
    );

    return replacement;
  }

  function removeLegacyMessages() {
    const forbidden = [
      "transcription is not supported by this browser",
      "browser speech transcription is unavailable",
      "mic unsupported",
    ];

    const observer = new MutationObserver(
      mutations => {
        for (const mutation of mutations) {
          const node = mutation.target;
          const text = String(
            node.textContent || ""
          ).toLowerCase();

          if (
            forbidden.some(message =>
              text.includes(message)
            )
          ) {
            node.textContent =
              "Use Talk to HALO for local transcription.";
          }
        }
      }
    );

    observer.observe(
      document.body,
      {
        subtree: true,
        childList: true,
        characterData: true,
      }
    );
  }

  function patchAllMicrophones() {
    [
      "#nbHaloMic",
      "#nbUniversalMic",
      "#nbVoiceOfflineMic",
      "[data-halo-mic]",
      ".halo-mic",
      ".mic-button",
    ].forEach(selector => {
      document
        .querySelectorAll(selector)
        .forEach(replaceButton);
    });
  }

  function install() {
    patchAllMicrophones();
    removeLegacyMessages();

    const observer = new MutationObserver(() => {
      patchAllMicrophones();
    });

    observer.observe(
      document.body,
      {
        childList: true,
        subtree: true,
      }
    );

    window.setInterval(
      patchAllMicrophones,
      1500
    );

    window.addEventListener("message", handleNativeMessage);

    window.NoorBrainHaloMicFinalFix = {
      version: VERSION,
      start: startRecording,
      stop: stopRecording,
      toggle,
      isRecording: () => state.recording,
      mode: () => state.mode,
      handleNativeMessage,
      patch: patchAllMicrophones,
    };

    console.info(
      `NoorBrain HALO Mic Final Fix ${VERSION} active`
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      install
    );
  } else {
    install();
  }
})();
