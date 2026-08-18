(() => {
  "use strict";

  const API = "/api/playback";
  const STORAGE_KEY = "noorbrain-auto-intercom-v126";
  const DEFAULT_TARGET = "existing-pi-audio";

  // VAD / timing config — tune from real-device behaviour.
  const CONFIG = {
    speechStartConfirmationMs: 200,
    speechEndSilenceMs: 700,
    minimumUtteranceMs: 250,
    noiseFloor: 0.018,
    hysteresis: 0.004,
    reconnectBackoffMs: 4000,
    guardMsAfterTalk: 400,
  };

  const STATE = {
    enabled: false,
    muted: false,

    // node
    nodes: [],
    targetNode: null,

    // session (auto-intercom owns its own session, segregated from manual)
    listenSession: "",
    listenActive: false,
    currentPlayer: null,
    pausePlayback: false,

    // talk
    talkMode: "idle",
    talkTarget: "",
    stream: null,
    recorder: null,
    chunks: [],
    recording: false,

    // VAD state
    speechStartAt: 0,
    speechConfirmed: false,
    lastSpeechAt: 0,
    speechLevel: 0,
    vadTimer: null,

    // reconnect
    reconnecting: false,
    reconnectTimer: null,
    stopRequested: false,
    initAttempted: false,
  };

  // ── helpers ────────────────────────────────────────────────────────────────

  function esc(v) {
    return String(v ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function status(message, mode = "") {
    const node = document.getElementById("nbAutoIntercomStatus");
    if (node) {
      node.textContent = message;
      node.dataset.mode = mode;
    }
  }

  async function api(path, options = {}) {
    const timeoutMs = Number(options.timeout || 130000);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const clean = { ...options };
    delete clean.timeout;
    try {
      const response = await fetch(API + path, {
        cache: "no-store",
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        signal: controller.signal,
        ...clean,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
      return payload;
    } catch (error) {
      if (error?.name === "AbortError") throw new Error("The room node request timed out.");
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  function isNative() {
    return new URLSearchParams(location.search).get("native_app") === "1" && window.parent !== window;
  }

  function savePref(key, value) {
    if (window.NoorBrainMobilePreferencesV12 && typeof window.NoorBrainMobilePreferencesV12.save === "function") {
      return window.NoorBrainMobilePreferencesV12.save(key, value);
    }
    try { localStorage.setItem(STORAGE_KEY, String(value)); } catch (_) {}
    return true;
  }

  function loadPref(key) {
    if (window.NoorBrainMobilePreferencesV12 && typeof window.NoorBrainMobilePreferencesV12.load === "function") {
      const v = window.NoorBrainMobilePreferencesV12.load(key);
      if (v !== undefined && v !== null) return String(v) === "1" || String(v) === "true";
    }
    try { return localStorage.getItem(STORAGE_KEY) === "1"; } catch (_) { return false; }
  }

  function nodeIsUsable(node) {
    return !!(node && node.online === true && node.trusted === true);
  }

  function selectedTargetNode() {
    if (STATE.targetNode && nodeIsUsable(STATE.targetNode)) return STATE.targetNode;
    const byId = STATE.nodes.find((n) => n.node_id === DEFAULT_TARGET);
    if (byId && nodeIsUsable(byId)) return byId;
    return STATE.nodes.find((n) => nodeIsUsable(n)) || null;
  }

  // ── VAD: lightweight RMS energy from accumulated chunks ────────────────────

  function rmsFromBlob(blob) {
    return blob.arrayBuffer().then((ab) => {
      const buf = new Uint8Array(ab);
      if (buf.length < 44) return 0;
      try {
        const samples = new Int16Array(buf.buffer, 44, Math.floor((buf.length - 44) / 2));
        if (samples.length < 10) return 0;
        let sum = 0;
        for (let i = 0; i < samples.length; i++) {
          const s = samples[i];
          sum += s * s;
        }
        return Math.sqrt(sum / samples.length) / 32768;
      } catch (_) {
        return 0;
      }
    });
  }

  function scheduleVadCheck() {
    if (STATE.vadTimer) return;
    STATE.vadTimer = setTimeout(() => {
      STATE.vadTimer = null;
      if (!STATE.recording || STATE.chunks.length === 0) return;
      (async () => {
        let totalRms = 0;
        let count = 0;
        for (const chunk of STATE.chunks) {
          const rms = await rmsFromBlob(chunk);
          totalRms += rms;
          count++;
        }
        if (count === 0) return;
        const avg = totalRms / count;
        STATE.speechLevel = avg;
        const now = Date.now();

        const isSpeech = avg >= CONFIG.noiseFloor;

        if (isSpeech) {
          STATE.lastSpeechAt = now;
          if (STATE.speechStartAt === 0) STATE.speechStartAt = now;
          if (now - STATE.speechStartAt >= CONFIG.speechStartConfirmationMs) {
            STATE.speechConfirmed = true;
          }
        }

        if (STATE.speechConfirmed && now - STATE.lastSpeechAt >= CONFIG.speechEndSilenceMs) {
          if (now - STATE.speechStartAt >= CONFIG.minimumUtteranceMs) {
            STATE.chunks = [];
            finishTalk("speech end");
          } else {
            STATE.speechStartAt = 0;
            STATE.speechConfirmed = false;
            STATE.chunks = [];
          }
        }
      })().catch(() => {});
    }, 120);
  }

  function cancelVad() {
    if (STATE.vadTimer) {
      clearTimeout(STATE.vadTimer);
      STATE.vadTimer = null;
    }
  }

  // ── audio player ───────────────────────────────────────────────────────────

  function stopCurrentPlayer() {
    if (STATE.currentPlayer) {
      try { STATE.currentPlayer.pause(); } catch (_) {}
      try { STATE.currentPlayer.src = ""; } catch (_) {}
      STATE.currentPlayer = null;
    }
  }

  function playChunk(encoded, format = "wav") {
    stopCurrentPlayer();
    if (STATE.muted || STATE.pausePlayback) return;
    try {
      const binary = atob(encoded);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: `audio/${format}` });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.volume = 1;
      const p = audio.play();
      if (p) p.catch(() => {});
      STATE.currentPlayer = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        if (STATE.currentPlayer === audio) STATE.currentPlayer = null;
      };
    } catch (_) {}
  }

  // ── state machine ──────────────────────────────────────────────────────────

  function setState(mode, message, statusMode) {
    STATE.talkMode = mode;
    if (message !== undefined) {
      status(message, statusMode);
      const ts = document.getElementById("nbAutoTalkStatus");
      if (ts) { ts.textContent = message; ts.dataset.mode = statusMode; }
    }
  }

  // ── auto listen loop ───────────────────────────────────────────────────────

  async function runListenLoop() {
    if (!STATE.listenActive || !STATE.listenSession) return;
    while (STATE.listenActive && STATE.listenSession && !STATE.stopRequested) {
      if (STATE.pausePlayback) {
        await new Promise((r) => setTimeout(r, 150));
        continue;
      }
      try {
        const chunk = await api(
          `/listen/${encodeURIComponent(STATE.listenSession)}/chunk?seconds=1`,
          { method: "POST", body: "{}", timeout: 14000 }
        );
        if (!STATE.listenActive) break;
        playChunk(chunk.audio_base64, chunk.format || "wav");
      } catch (error) {
        if (STATE.stopRequested) break;
        console.warn("AUTO_INTERCOM_LISTEN_ERROR", error.message);
        await handleListenFailure(error);
        break;
      }
    }
  }

  async function handleListenFailure(error) {
    if (STATE.stopRequested) return;
    stopCurrentPlayer();
    STATE.listenActive = false;
    const session = STATE.listenSession;
    STATE.listenSession = "";
    setState("reconnecting", "Reconnecting…", "reconnecting");
    await cleanupRemoteSession(session);
    if (STATE.enabled && !STATE.stopRequested) {
      await scheduleReconnect();
    } else {
      setState("idle", "Off", "idle");
    }
  }

  async function cleanupRemoteSession(session) {
    if (!session) return;
    try {
      await api(`/listen/${encodeURIComponent(session)}/stop`, { method: "POST", body: "{}", timeout: 10000 });
    } catch (_) {}
  }

  async function scheduleReconnect() {
    if (STATE.reconnectTimer) return;
    STATE.reconnecting = true;
    STATE.reconnectTimer = setTimeout(async () => {
      STATE.reconnectTimer = null;
      if (!STATE.enabled || STATE.stopRequested) {
        setState("idle", "Off", "idle");
        STATE.reconnecting = false;
        return;
      }
      try {
        const target = selectedTargetNode();
        if (!target) {
          setState("error", "No trusted room node available.", "error");
          STATE.reconnecting = false;
          return;
        }
        await startListen(target);
      } catch (error) {
        console.warn("AUTO_INTERCOM_RECONNECT_FAILED", error.message);
        setState("error", "Reconnect failed — retrying…", "error");
        STATE.reconnecting = false;
        await scheduleReconnect();
      }
    }, CONFIG.reconnectBackoffMs);
  }

  // ── start / stop listen ─────────────────────────────────────────────────────

  async function startListen(target) {
    if (!target) throw new Error("No trusted room node configured.");
    if (!nodeIsUsable(target)) throw new Error("Target room node is offline or not trusted.");
    if (STATE.listenActive) await stopListen(false);

    STATE.targetNode = target;
    setState("listening_to_room", `Connected · ${esc(target.name)} · Listening to Room`, "listening");

    const result = await api(`/listen/start/${encodeURIComponent(target.node_id)}`, {
      method: "POST", body: "{}", timeout: 14000,
    });
    const nodeSession = String(result.session_id || "");
    if (!nodeSession) throw new Error("Room node did not acknowledge listening.");

    STATE.listenSession = result.session_id || "";
    STATE.listenActive = true;
    STATE.pausePlayback = false;

    status(`Listening to Room · ${esc(target.name)}`, "listening");
    runListenLoop();
  }

  async function stopListen(silent = true) {
    STATE.stopRequested = true;
    STATE.listenActive = false;
    STATE.pausePlayback = false;
    stopCurrentPlayer();
    const session = STATE.listenSession;
    STATE.listenSession = "";
    if (session) await cleanupRemoteSession(session);
    if (!silent) setState("idle", "Off", "idle");
  }

  // ── auto talk ──────────────────────────────────────────────────────────────

  async function startPhoneCapture() {
    if (STATE.recording) return false;
    // Accept any talkMode; half-duplex is enforced by pausing room playback.
    if (!window.navigator?.mediaDevices?.getUserMedia) {
      throw new Error("This browser does not support microphone capture.");
    }

    STATE.pausePlayback = true;
    stopCurrentPlayer();

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });

    STATE.stream = stream;
    STATE.chunks = [];
    STATE.recording = true;
    STATE.speechStartAt = 0;
    STATE.speechConfirmed = false;
    STATE.lastSpeechAt = 0;
    STATE.speechLevel = 0;

    const mimeType =
      ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"].find(
        (t) => MediaRecorder.isTypeSupported(t)
      ) || "";

    const recorder = new MediaRecorder(stream, mimeType ? { mimeType, audioBitsPerSecond: 64000 } : {});
    STATE.recorder = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) STATE.chunks.push(event.data);
    };

    recorder.onerror = () => {
      if (STATE.talkMode === "phone_speech_detected" || STATE.talkMode === "talking_to_room") {
        finishTalk("microphone error");
      }
    };

    recorder.onstop = async () => {
      STATE.recording = false;
      STATE.pausePlayback = false;
      if (STATE.talkMode !== "phone_speech_detected" && STATE.talkMode !== "talking_to_room") return;
      await finishTalk("recording stopped");
    };

    recorder.start(100);
    STATE.talkMode = "phone_speech_detected";
    setState("phone_speech_detected", "Detecting speech…", "detecting");
    scheduleVadCheck();
    return true;
  }

  async function finishTalk(reason) {
    cancelVad();
    STATE.recording = false;
    STATE.pausePlayback = false;

    let blob = null;
    if (STATE.chunks.length) {
      const raw = new Blob(STATE.chunks, { type: STATE.recorder?.mimeType || "audio/webm" });
      if (raw.size > 800) blob = raw;
    }
    STATE.chunks = [];

    STATE.stream?.getTracks().forEach((t) => t.stop());
    STATE.stream = null;
    STATE.recorder = null;

    if (STATE.talkMode === "idle") return;

    if (!blob || blob.size < 44) {
      if (STATE.talkMode === "phone_speech_detected") {
        STATE.talkMode = "returning_to_listen";
        setState("returning_to_listen", "Returning to listen…", "returning");
        await new Promise((r) => setTimeout(r, 200));
        return resumeListen();
      }
      STATE.talkMode = "idle";
      setState("idle", "Off", "idle");
      return;
    }

    const hadSpeech = STATE.talkMode === "phone_speech_detected" || STATE.talkMode === "talking_to_room";
    if (!hadSpeech) {
      STATE.talkMode = "idle";
      setState("idle", "Off", "idle");
      return;
    }

    STATE.talkMode = "talking_to_room";
    setState("talking_to_room", "Sending to room…", "talking");

    try {
      await sendToPi(blob);
      setState("returning_to_listen", "Sent · Returning to listen…", "returning");
      await new Promise((r) => setTimeout(r, CONFIG.guardMsAfterTalk));
      return resumeListen();
    } catch (error) {
      console.warn("AUTO_INTERCOM_TALK_SEND_FAILED", error.message);
      setState("error", `Talk failed: ${error.message}`, "error");
      await new Promise((r) => setTimeout(r, 800));
      return resumeListen();
    }
  }

  async function sendToPi(blob) {
    const encoded = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("Audio encoding failed"));
      reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
      reader.readAsDataURL(blob);
    });
    if (!encoded) throw new Error("Audio encoding produced empty payload");

    const format = blob.type.includes("webm") ? "webm" : "wav";
    const result = await api(`/talk/${encodeURIComponent(STATE.talkTarget)}`, {
      method: "POST",
      body: JSON.stringify({ audio_base64: encoded, format }),
      timeout: 180000,
    });
    if (String(result.status || "") === "played") return result;
    throw new Error(String(result.detail || result.message || "Talk playback was not acknowledged"));
  }

  async function resumeListen() {
    STATE.talkMode = "idle";
    STATE.pausePlayback = false;
    stopCurrentPlayer();
    const target = STATE.targetNode;
    if (!target || !STATE.enabled || STATE.stopRequested) {
      if (STATE.enabled && !STATE.stopRequested) {
        await scheduleReconnect();
      } else {
        setState("idle", STATE.muted ? "Muted" : "Off", STATE.muted ? "muted" : "idle");
      }
      return;
    }
    try {
      await startListen(target);
    } catch (error) {
      console.warn("AUTO_INTERCOM_RESUME_FAILED", error.message);
      setState("error", "Resume failed — retrying…", "error");
      await scheduleReconnect();
    }
  }

  // ── public lifecycle ───────────────────────────────────────────────────────

  async function startAutoIntercom() {
    if (STATE.initAttempted && STATE.enabled) return;
    STATE.initAttempted = true;
    if (!STATE.enabled || STATE.stopRequested) return;

    stopCurrentPlayer();
    setState("initializing", "Starting auto intercom…", "initializing");

    try {
      const nodes = await api("/nodes?probe=true");
      STATE.nodes = nodes.nodes || [];
    } catch (error) {
      console.warn("AUTO_INTERCOM_NODE_LIST_FAILED", error.message);
      setState("error", `Cannot reach NoorBrain: ${error.message}`, "error");
      await scheduleReconnect();
      return;
    }

    const target = selectedTargetNode();
    if (!target) {
      setState("error", "No trusted Raspberry Pi found. Add one in Rooms & Speakers.", "error");
      return;
    }

    STATE.targetNode = target;
    STATE.talkTarget = target.node_id;
    await startListen(target);
  }

  async function stopAutoIntercom() {
    STATE.enabled = false;
    STATE.stopRequested = true;
    STATE.initAttempted = false;
    cancelVad();
    if (STATE.reconnectTimer) { clearTimeout(STATE.reconnectTimer); STATE.reconnectTimer = null; }
    STATE.reconnecting = false;
    await stopListen(true);
    STATE.talkMode = "idle";
    STATE.pausePlayback = false;
    STATE.targetNode = null;
    STATE.talkTarget = "";
    STATE.nodes = [];
    stopCurrentPlayer();
    setState("idle", "Off", "idle");
    status("Off", "idle");
    savePref("auto_intercom_enabled", "0");
  }

  // ── public API ─────────────────────────────────────────────────────────────

  const PublicAPI = Object.freeze({
    version: "1.0.0",
    start: startAutoIntercom,
    stop: stopAutoIntercom,
    setMuted(muted) {
      STATE.muted = !!muted;
      const btn = document.getElementById("nbAutoMuteBtn");
      if (btn) {
        btn.textContent = muted ? "Muted · Tap to Unmute" : "Mute";
      }
      if (muted) stopCurrentPlayer();
      status(muted ? "Muted" : (STATE.enabled ? "Listening to Room" : "Off"),
             muted ? "muted" : (STATE.enabled ? "listening" : "idle"));
      savePref("auto_intercom_muted", muted ? "1" : "0");
    },
    isEnabled() { return STATE.enabled; },
    isMuted() { return STATE.muted; },
    isListening() { return STATE.listenActive; },
    talkMode() { return STATE.talkMode; },
  });

  window.NoorBrainAutoIntercomV126 = PublicAPI;

  // ── lifecycle ──────────────────────────────────────────────────────────────

  document.addEventListener("pagehide", () => {
    if (STATE.listenSession) stopListen(true).catch(() => {});
    STATE.stream?.getTracks().forEach((t) => t.stop());
    STATE.stream = null;
    STATE.recorder = null;
    cancelVad();
    STATE.recording = false;
    STATE.talkMode = "idle";
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && STATE.listenActive) {
      stopCurrentPlayer();
    }
  });

  // Auto-start if enabled and DOM is ready.
  if (loadPref("auto_intercom_enabled")) {
    STATE.enabled = true;
    if (document.readyState === "complete") {
      setTimeout(() => API.start().catch(console.warn), 500);
    } else {
      window.addEventListener("load", () => setTimeout(() => API.start().catch(console.warn), 500));
    }
  }

  // Notify other scripts when state changes.
  function broadcast() {
    window.dispatchEvent(new CustomEvent("noorbrain:auto-intercom-state-changed", {
      detail: {
        enabled: STATE.enabled,
        muted: STATE.muted,
        listening: STATE.listenActive,
        talkMode: STATE.talkMode,
      }
    }));
  }

  // Override setState to also broadcast.
  const _setState = setState;
  setState = function(mode, message, statusMode) {
    _setState(mode, message, statusMode);
    broadcast();
  };

  console.log("NOORBRAIN_AUTO_INTERCOM_V126_LOADED", { enabled: STATE.enabled });
})();
