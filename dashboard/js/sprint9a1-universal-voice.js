(() => {
  "use strict";

  if (window.NoorBrainUniversalVoice?.installed) return;

  const API = "/api/universal-voice-v9";
  const state = {
    listening: false,
    recognition: null,
    lastTranscript: "",
    lastAt: 0,
  };

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {"Content-Type": "application/json"},
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `Voice gateway HTTP ${response.status}`);
    return body;
  }

  function capabilities() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    return {
      secure_context: window.isSecureContext,
      browser_recognition: Boolean(Recognition),
      audio_capture: Boolean(navigator.mediaDevices?.getUserMedia),
      speech_output: Boolean(window.speechSynthesis),
    };
  }

  async function send(transcript, options = {}) {
    const clean = String(transcript || "").replace(/\s+/g, " ").trim();
    if (!clean) throw new Error("Please say or type a command.");
    const now = Date.now();
    if (clean.toLowerCase() === state.lastTranscript && now - state.lastAt < 1500) {
      return {status: "duplicate", accepted: false, duplicate: true};
    }
    state.lastTranscript = clean.toLowerCase();
    state.lastAt = now;

    const result = await api("/prepare", {
      method: "POST",
      body: JSON.stringify({
        session_id: options.session_id || localStorage.getItem("noorbrain.voice.session") || "home",
        transcript: clean,
        source: options.source || "browser",
      }),
    });

    if (result.accepted) {
      window.dispatchEvent(new CustomEvent("noorbrain:voice-command-ready", {
        detail: result,
      }));
    }
    return result;
  }

  function listen(options = {}) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      const detail = capabilities().audio_capture
        ? "Audio capture works, but this browser has no live speech recognition."
        : "Microphone is unavailable. Use HTTPS, localhost, or type your command.";
      window.dispatchEvent(new CustomEvent("noorbrain:voice-unavailable", {detail}));
      return Promise.reject(new Error(detail));
    }
    if (state.listening) return Promise.reject(new Error("HALO is already listening."));

    return new Promise((resolve, reject) => {
      const recognition = new Recognition();
      state.recognition = recognition;
      state.listening = true;
      recognition.lang = options.lang || document.documentElement.lang || "en-CA";
      recognition.interimResults = false;
      recognition.continuous = false;

      recognition.onresult = async event => {
        try {
          const transcript = event.results?.[0]?.[0]?.transcript || "";
          resolve(await send(transcript, {...options, source: "browser-speech"}));
        } catch (error) {
          reject(error);
        }
      };
      recognition.onerror = event => reject(new Error(event.error || "Voice recognition failed."));
      recognition.onend = () => {
        state.listening = false;
        state.recognition = null;
      };
      recognition.start();
    });
  }

  function stop() {
    state.recognition?.stop();
    state.listening = false;
  }

  window.NoorBrainUniversalVoice = Object.freeze({
    installed: true,
    version: "9.1.0",
    capabilities,
    send,
    listen,
    stop,
  });
})();
