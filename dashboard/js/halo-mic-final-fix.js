(() => {
  "use strict";

  const VERSION = "3.3.0";
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
    diagnostics: [],
    nativeSessionId: "",
  };

  function trace(event, detail = {}) {
    const entry = {event, at: new Date().toISOString(), ...detail};
    state.diagnostics.push(entry);
    state.diagnostics = state.diagnostics.slice(-100);
    console.info("HALO_VOICE_EVENT", entry);
    if (
      typeof window.dispatchEvent === "function"
      && typeof window.CustomEvent === "function"
    ) {
      window.dispatchEvent(new window.CustomEvent(
        "noorbrain:halo-voice-event",
        {detail: entry}
      ));
    }
    return entry;
  }

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
    state.nativeSessionId = "";
    setMode("idle", message, mode);
    trace("VOICE_IDLE", {message: String(message || "")});
  }

  function fail(error, fallback = "Voice processing failed.") {
    const message = String(error?.message || error || fallback);
    trace("VOICE_ERROR", {message});
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
    trace("TRANSCRIBE_START", {bytes: Number(blob?.size || 0)});
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

    trace("TRANSCRIBE_RESULT", {
      text: String(payload.text || payload.command || "").slice(0, 200)
    });
    return payload;
  }

  async function sendToHalo(command) {
    const clean = String(command || "").trim();

    if (!clean) {
      throw new Error(
        "No command was detected."
      );
    }

    // Require the wake word ("noor", "hey noor", "hello noor")
    // before sending to HALO. This prevents ambient noise or
    // non-directed speech from waking the assistant.
    // Normalize: strip punctuation that STT may insert after the wake word
    // e.g. "noor, what time is it" → "noor what time is it"
    const WAKE_WORDS = ["noor", "hey noor", "hello noor"];
    const normalized = clean.toLowerCase().trim()
      .replace(/([\w])([.,;:\-]+)/g, "$1 ");
    const hasWake = WAKE_WORDS.some(
      w => normalized === w || normalized.startsWith(w + " ")
    );

    if (!hasWake) {
      trace("WAKEWORD_MISS", {
        text: clean.slice(0, 200),
        reason: "No wake word detected",
      });
      setStatus(
        "Say \"Noor\" to wake HALO.",
        "ignored"
      );
      return {status: "ignored", reply: ""};
    }

    // Strip the wake word from the command text before sending to HALO
    const wakeMatch = WAKE_WORDS.find(
      w => normalized === w || normalized.startsWith(w + " ")
    );
    if (wakeMatch && normalized === wakeMatch) {
      command = "";
    } else if (wakeMatch) {
      // Use the normalized version to find the slice point, then apply
      // to the original clean text to preserve original casing/spacing
      const normalizedRest = normalized.slice(wakeMatch.length).replace(/^[\s,.\-]+/, "");
      command = normalizedRest;
    }

    // Update the input field with the original transcription
    const input = inputNode();
    if (input) {
      input.value = clean;
    }

    // Use the wake-word-stripped command for HALO
    const haloText = command;
    trace("CHAT_START", {text: haloText.slice(0, 200)});

    if (
      window.NoorBrainMobile126
      && typeof window.NoorBrainMobile126
        .sendHalo === "function"
    ) {
      const result = await window.NoorBrainMobile126.sendHalo(haloText);
      trace("CHAT_RESULT", {
        reply: String(result?.reply || result?.message || "").slice(0, 200)
      });
      trace("TTS_SENT", {transport: "v126"});
      return;
    }

    if (
      window.NoorBrainHaloOneClick
      && typeof window.NoorBrainHaloOneClick
        .sendCommand === "function"
    ) {
      const result = await window.NoorBrainHaloOneClick
        .sendCommand(haloText);
      trace("CHAT_RESULT", {
        reply: String(result?.reply || result?.message || "").slice(0, 200)
      });
      trace("TTS_SENT", {transport: "oneclick"});
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
          message: haloText,
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
            message: haloText,
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
      trace("CHAT_RESULT", {
        reply: String(halo.reply || halo.message || "").slice(0, 200)
      });
      return;
    }

    setStatus(
      payload.reply || "Done.",
      "done"
    );
    trace("CHAT_RESULT", {
      reply: String(payload.reply || "Done.").slice(0, 200)
    });
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

  function nativePlugins() {
    return window.Capacitor?.Plugins || {};
  }

  function postNativeCommand(action, reason = "") {
    if (!state.nativeSessionId) {
      state.nativeSessionId = `halo-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    }
    window.parent.postMessage(
      {
        type: "noorbrain-native-record-toggle",
        action,
        reason,
        session_id: state.nativeSessionId,
      },
      "*"
    );
  }

  function base64Blob(value, mimeType = "audio/mp4") {
    const clean = String(value || "")
      .replace(/^data:[^,]+,/, "")
      .replace(/\s+/g, "");
    const binary = window.atob(clean);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return new Blob([bytes], {type: mimeType});
  }

  async function nativeRecordingBlob(result) {
    if (result?.blob instanceof Blob) return result.blob;

    const mimeType = result?.mimeType || result?.mime_type || "audio/mp4";
    const encoded = result?.recordDataBase64 || result?.base64 || result?.data;
    if (encoded && typeof encoded === "string") {
      return base64Blob(encoded, mimeType);
    }

    const filePath = result?.filePath || result?.uri || result?.path;
    if (!filePath) {
      throw new Error("Android recorder returned no audio file.");
    }

    const filesystem = nativePlugins().Filesystem;
    if (filesystem?.readFile) {
      const file = await filesystem.readFile({path: filePath});
      if (file?.data) return base64Blob(file.data, mimeType);
    }

    const converted = window.Capacitor?.convertFileSrc?.(filePath) || filePath;
    const response = await fetch(converted, {cache: "no-store"});
    if (!response.ok) {
      throw new Error(`Cannot read Android recording (HTTP ${response.status}).`);
    }
    return response.blob();
  }

  async function startNative(button) {
    if (state.mode !== "idle") return false;

    state.operation += 1;
    const operation = state.operation;
    state.activeButton = button || null;
    state.nativeTranscriptHandled = false;
    setMode("starting", "Starting microphone…", "thinking");
    trace("MIC_REQUEST", {native: true});

    scheduleTimer(() => {
      fail("The Android microphone did not start. Tap to try again.");
    }, NATIVE_START_TIMEOUT_MS);

    const recorder = nativePlugins().CapacitorAudioRecorder;
    if (!recorder?.startRecording || !recorder?.stopRecording) {
      trace("NATIVE_START_SENT", {transport: "parent-relay"});
      postNativeCommand("start");
      return true;
    }

    trace("NATIVE_START_SENT", {transport: "capacitor-direct"});
    const permission = await recorder.requestPermissions?.();
    const permissionState =
      permission?.recordAudio || permission?.microphone || "granted";
    if (permissionState !== "granted") {
      throw new Error("Microphone permission was denied in Android settings.");
    }
    trace("NATIVE_START_ACK", {permission: permissionState});

    await recorder.startRecording({sampleRate: 16000, bitRate: 64000});
    if (operation !== state.operation) return false;

    clearTimer();
    setMode("listening", "Listening… tap again when finished.", "listening");
    trace("RECORDING_STARTED", {native: true});
    scheduleTimer(() => stopNative("automatic timeout"), RECORDING_TIMEOUT_MS);
    return true;
  }

  async function stopNative(reason = "second tap") {
    if (state.mode !== "listening") return false;

    const operation = state.operation;
    clearTimer();
    setMode(
      "stopping",
      reason === "automatic timeout"
        ? "Recording limit reached. Processing voice…"
        : "Processing voice…",
      "thinking"
    );
    trace("STOP_REQUEST", {reason});

    scheduleTimer(() => {
      fail("Android voice processing timed out. Tap to try again.");
    }, PROCESSING_TIMEOUT_MS);

    const recorder = nativePlugins().CapacitorAudioRecorder;
    if (!recorder?.stopRecording) {
      postNativeCommand("stop", reason);
      return true;
    }

    try {
      const result = await recorder.stopRecording();
      if (operation !== state.operation) return false;
      trace("NATIVE_STOP_ACK", {native: true, transport: "capacitor-direct"});
      setMode("processing", "Transcribing on NoorBrain…", "thinking");

      const blob = await nativeRecordingBlob(result);
      trace("NATIVE_AUDIO_RECEIVED", {
        bytes: blob.size,
        mimeType: blob.type || result?.mimeType || "unknown"
      });
      if (blob.size < 500) {
        throw new Error("Recording was empty or too short. Please try again.");
      }

      const transcript = await transcribe(blob);
      const text = String(transcript.command || transcript.text || "").trim();
      if (!text) throw new Error("No clear speech detected. Please try again.");

      setMode("conversation", `Heard: ${text}`, "heard");
      await sendToHalo(text);
      if (operation === state.operation) reset();
      return true;
    } catch (error) {
      if (operation === state.operation) fail(error, "Android voice processing failed.");
      return false;
    }
  }

  async function handleNativeMessage(event) {
    if (!isNativeApp()) return false;
    const data = event?.data || {};
    const nativeEvent = String(data.event || "");

    if (data.type === "noorbrain-native-start-ack" || nativeEvent === "NATIVE_START_ACK") {
      if (state.mode !== "starting") return false;
      trace("NATIVE_START_ACK", {transport: "parent-relay"});
      return true;
    }

    if (data.type === "noorbrain-native-listening" || nativeEvent === "RECORDING_STARTED") {
      if (state.mode !== "starting") return false;
      if (!nativeEvent) {
        trace("NATIVE_START_ACK", {transport: "parent-relay", legacy: true});
      }
      setMode(
        "listening",
        "Listening… tap again when finished.",
        "listening"
      );
      trace("RECORDING_STARTED", {native: true, transport: "parent-relay"});
      scheduleTimer(() => stopNative("automatic timeout"), RECORDING_TIMEOUT_MS);
      return true;
    }

    if (data.type === "noorbrain-native-stop-ack" || nativeEvent === "NATIVE_STOP_ACK") {
      if (!["listening", "stopping"].includes(state.mode)) return false;
      trace("NATIVE_STOP_ACK", {transport: "parent-relay"});
      return true;
    }

    if (data.type === "noorbrain-native-audio-received" || nativeEvent === "NATIVE_AUDIO_RECEIVED") {
      if (!["stopping", "processing"].includes(state.mode)) return false;
      trace("NATIVE_AUDIO_RECEIVED", {
        transport: "parent-relay",
        base64Bytes: Number(data.base64_bytes || 0),
      });
      return true;
    }

    if (data.type === "noorbrain-native-processing" || nativeEvent === "TRANSCRIBE_START") {
      if (!["listening", "stopping"].includes(state.mode)) return false;
      clearTimer();
      setMode("processing", "Transcribing on NoorBrain…", "thinking");
      trace("TRANSCRIBE_START", {transport: "parent-relay"});
      scheduleTimer(() => {
        fail("Android transcription timed out. Tap to try again.");
      }, PROCESSING_TIMEOUT_MS);
      return true;
    }

    if (data.type === "noorbrain-native-error" || nativeEvent === "NATIVE_START_ERROR" || nativeEvent === "VOICE_ERROR") {
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

    trace("TRANSCRIBE_RESULT", {text: text.slice(0, 200), transport: "parent-relay"});

    const operation = state.operation;
    setMode("conversation", `Heard: ${text}`, "heard");

    try {
      await sendToHalo(text);
      if (operation === state.operation) {
        window.parent.postMessage(
          {
            type: "noorbrain-native-conversation-complete",
            session_id: state.nativeSessionId,
          },
          "*"
        );
        state.nativeSessionId = "";
        reset();
      }
    } catch (error) {
      if (operation === state.operation) fail(error, "Noor request failed.");
    }
    return true;
  }

  function toggle(button) {
    if (isNativeApp()) {
      if (state.mode === "listening") return stopNative();
      if (state.mode !== "idle") return Promise.resolve(false);
      return startNative(button).catch(error =>
        fail(error, "Android microphone failed.")
      );
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
      diagnostics: () => [...state.diagnostics],
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
