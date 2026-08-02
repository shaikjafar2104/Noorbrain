(() => {
  "use strict";

  if (window.NoorBrainVoiceRepeatGuard?.installed) return;

  const state = {
    installed: true,
    version: "8.3.0",
    lastText: "",
    lastAt: 0,
    speakingText: "",
    speaking: false,
    lastActionAt: 0,
    blocked: 0,
    userActivated: false,
    bootMuteUntil: Date.now() + 8000,
  };

  const SAME_REPLY_WINDOW_MS = 12000;
  const ACTION_WINDOW_MS = 1200;
  const STORAGE_KEY = "noorbrain.voice.last-spoken.v1";

  function normalize(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function readShared() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch (_) {
      return {};
    }
  }

  function writeShared(text, at) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({text, at}));
    } catch (_) {}
  }

  function recentlySpoken(text, now = Date.now()) {
    const normalized = normalize(text);
    if (!normalized) return true;

    if (
      normalized === state.speakingText ||
      (normalized === state.lastText && now - state.lastAt < SAME_REPLY_WINDOW_MS)
    ) {
      return true;
    }

    const shared = readShared();
    return (
      normalize(shared.text) === normalized &&
      now - Number(shared.at || 0) < SAME_REPLY_WINDOW_MS
    );
  }

  function installSpeechGuard() {
    const synth = window.speechSynthesis;
    if (!synth || typeof synth.speak !== "function") return false;
    if (synth.speak.__noorbrainGuarded) return true;

    const nativeSpeak = synth.speak.bind(synth);
    const guardedSpeak = function (utterance) {
      const text = normalize(utterance?.text);
      const now = Date.now();

      if (!state.userActivated && now < state.bootMuteUntil) {
        state.blocked += 1;
        window.speechSynthesis?.cancel();
        return;
      }

      if (recentlySpoken(text, now)) {
        state.blocked += 1;
        window.dispatchEvent(new CustomEvent("noorbrain:voice-duplicate-blocked", {
          detail: {text, blocked: state.blocked},
        }));
        return;
      }

      state.lastText = text;
      state.lastAt = now;
      state.speakingText = text;
      state.speaking = true;
      writeShared(text, now);

      const finish = () => {
        if (state.speakingText === text) {
          state.speakingText = "";
          state.speaking = false;
        }
      };

      utterance.addEventListener?.("end", finish, {once: true});
      utterance.addEventListener?.("error", finish, {once: true});
      nativeSpeak(utterance);
    };

    guardedSpeak.__noorbrainGuarded = true;
    synth.speak = guardedSpeak;
    return true;
  }

  function isVoiceAction(target) {
    const button = target?.closest?.("button, [role='button']");
    if (!button) return false;

    const identity = [
      button.id,
      button.className,
      button.getAttribute("aria-label"),
      button.textContent,
    ].join(" ").toLowerCase();

    return /talk to halo|ask halo|send|push.to.talk|microphone|\bmic\b|voice/.test(identity);
  }

  document.addEventListener("click", event => {
    if (!isVoiceAction(event.target)) return;

    const now = Date.now();
    if (now - state.lastActionAt < ACTION_WINDOW_MS) {
      event.preventDefault();
      event.stopImmediatePropagation();
      state.blocked += 1;
      return;
    }
    state.lastActionAt = now;
  }, true);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && window.speechSynthesis?.speaking) {
      window.speechSynthesis.cancel();
      state.speaking = false;
      state.speakingText = "";
    }
  });

  window.addEventListener("pagehide", () => {
    window.speechSynthesis?.cancel();
  });


  function activateVoiceFromUser(event) {
    if (event?.isTrusted === false) return;
    state.userActivated = true;
    state.bootMuteUntil = 0;
  }

  for (const eventName of ["pointerdown", "touchstart", "keydown"]) {
    document.addEventListener(eventName, activateVoiceFromUser, {
      capture: true,
      passive: true,
      once: true,
    });
  }

  function cancelStartupVoice() {
    if (!state.userActivated && Date.now() < state.bootMuteUntil) {
      window.speechSynthesis?.cancel();
    }
  }

  cancelStartupVoice();
  setTimeout(cancelStartupVoice, 100);
  setTimeout(cancelStartupVoice, 500);
  setTimeout(cancelStartupVoice, 1500);

  installSpeechGuard();
  setTimeout(installSpeechGuard, 500);
  setTimeout(installSpeechGuard, 2000);

  window.NoorBrainVoiceRepeatGuard = Object.freeze({
    installed: true,
    version: state.version,
    status: () => ({...state}),
    reset: () => {
      state.lastText = "";
      state.lastAt = 0;
      state.speakingText = "";
      state.speaking = false;
      try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
      window.speechSynthesis?.cancel();
    },
  });
})();
