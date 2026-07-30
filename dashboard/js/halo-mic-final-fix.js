(() => {
  "use strict";

  const VERSION = "3.0.0";
  const VOICE_API = "/api/halo-voice";
  const state = {
    recorder: null,
    stream: null,
    chunks: [],
    recording: false,
    activeButton: null,
  };

  function statusNode() {
    return document.querySelector(
      "#nbUniversalVoiceStatus, #nbHaloReply, [data-halo-reply]"
    );
  }

  function inputNode() {
    return document.querySelector(
      "#nbHaloInput, [data-halo-input]"
    );
  }

  function setStatus(message, mode = "") {
    const nodes = document.querySelectorAll(
      "#nbUniversalVoiceStatus, #nbHaloReply, [data-halo-reply]"
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
    state.recording = true;
    state.activeButton = button;

    recorder.ondataavailable = event => {
      if (event.data && event.data.size > 0) {
        state.chunks.push(event.data);
      }
    };

    recorder.onerror = event => {
      setStatus(
        event.error?.message
        || "Microphone recording failed.",
        "error"
      );
    };

    recorder.onstop = async () => {
      state.recording = false;

      state.stream
        ?.getTracks()
        .forEach(track => track.stop());

      setButtonsRecording(false);
      setStatus(
        "Transcribing on NoorBrain…",
        "thinking"
      );

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

        setStatus(
          `Heard: ${result.text}`,
          "heard"
        );

        await sendToHalo(command);
      } catch (error) {
        setStatus(
          error.message
          || "Voice processing failed.",
          "error"
        );
      } finally {
        state.chunks = [];
        state.recorder = null;
        state.stream = null;
        state.activeButton = null;
      }
    };

    recorder.start(250);
    setButtonsRecording(true);

    setStatus(
      "Listening… speak for 3–8 seconds, then press Stop.",
      "listening"
    );
  }

  function stopRecording() {
    if (
      state.recorder
      && state.recording
      && state.recorder.state !== "inactive"
    ) {
      state.recorder.stop();
    }
  }

  function toggle(button) {
    if (state.recording) {
      stopRecording();
      return;
    }

    startRecording(button).catch(error => {
      setStatus(
        error.message
        || "Microphone failed.",
        "error"
      );
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

    window.NoorBrainHaloMicFinalFix = {
      version: VERSION,
      start: startRecording,
      stop: stopRecording,
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
