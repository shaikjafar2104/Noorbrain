(() => {
  "use strict";

  if (window.NoorBrainElectronicVoiceOff?.installed) return;

  const silent = () => false;

  function cancelBrowserSpeech() {
    try { window.speechSynthesis?.cancel(); } catch (_) {}
  }

  function blockBrowserSpeech() {
    cancelBrowserSpeech();
    const synth = window.speechSynthesis;
    if (!synth) return;

    try {
      Object.defineProperty(synth, "speak", {
        configurable: true,
        writable: false,
        value: silent,
      });
    } catch (_) {
      try { synth.speak = silent; } catch (_) {}
    }
  }

  try {
    Object.defineProperty(window, "NoorBrainHALOSpeak", {
      configurable: false,
      get: () => silent,
      set: silent,
    });
  } catch (_) {
    window.NoorBrainHALOSpeak = silent;
  }

  async function persistSilentStartup() {
    try {
      await fetch("/api/voice-platform-v9/config", {
        method: "PATCH",
        cache: "no-store",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({startup_speech: false}),
      });
    } catch (_) {}
  }

  blockBrowserSpeech();
  document.addEventListener("DOMContentLoaded", blockBrowserSpeech);
  window.addEventListener("pageshow", blockBrowserSpeech);
  document.addEventListener("visibilitychange", cancelBrowserSpeech);
  window.setTimeout(blockBrowserSpeech, 250);
  window.setTimeout(blockBrowserSpeech, 1200);
  window.setTimeout(persistSilentStartup, 400);

  window.NoorBrainElectronicVoiceOff = Object.freeze({
    installed: true,
    version: "16.0.0",
    cancel: cancelBrowserSpeech,
  });
})();
