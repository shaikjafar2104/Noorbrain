(() => {
  "use strict";

  if (window.NoorBrainHaloVoiceRepeatFix) return;

  const state = {
    lastText: "",
    lastSpokenAt: 0,
    speaking: false,
    cooldownMs: 5000,
  };

  function normalize(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function shouldIgnore(text) {
    const value = normalize(text);
    if (!value) return true;

    const blocked = [
      "listening",
      "thinking",
      "transcribing",
      "preparing",
      "heard:",
      "voice backend http",
      "microphone",
      "saved.",
      "ready.",
    ];

    return blocked.some(item =>
      value.toLowerCase().startsWith(item)
    );
  }

  function safeSpeak(text) {
    const value = normalize(text);
    const now = Date.now();

    if (
      shouldIgnore(value)
      || state.speaking
      || (
        value === state.lastText
        && now - state.lastSpokenAt < state.cooldownMs
      )
    ) {
      return false;
    }

    state.lastText = value;
    state.lastSpokenAt = now;
    state.speaking = true;

    try {
      speechSynthesis.cancel();

      const selector =
        window.NoorBrainHaloVoiceSelector;

      if (
        selector
        && typeof selector.speak === "function"
      ) {
        selector.speak(value);
      } else {
        const utterance =
          new SpeechSynthesisUtterance(value);

        utterance.onend = () => {
          state.speaking = false;
        };

        utterance.onerror = () => {
          state.speaking = false;
        };

        speechSynthesis.speak(utterance);
        return true;
      }

      window.setTimeout(() => {
        state.speaking = false;
      }, Math.max(1500, value.length * 70));

      return true;
    } catch (_) {
      state.speaking = false;
      return false;
    }
  }

  function disableLegacyObserverSpeech() {
    const selector =
      window.NoorBrainHaloVoiceSelector;

    if (!selector) return;

    selector.autoSpeakEnabled = false;
  }

  function installObserver() {
    let timer = null;

    const observer = new MutationObserver(() => {
      window.clearTimeout(timer);

      timer = window.setTimeout(() => {
        const reply = document.querySelector(
          "#nbHaloReply, [data-halo-reply]"
        );

        const text = normalize(
          reply?.textContent
        );

        safeSpeak(text);
      }, 400);
    });

    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
    });
  }

  function install() {
    speechSynthesis.cancel();
    disableLegacyObserverSpeech();
    installObserver();

    window.NoorBrainHaloVoiceRepeatFix = {
      version: "1.0.0",
      speak: safeSpeak,
      stop() {
        speechSynthesis.cancel();
        state.speaking = false;
      },
      state,
    };

    console.info(
      "NoorBrain HALO Voice Repeat Loop Fix active"
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
