(() => {
  "use strict";

  if (window.NoorBrainUniversalVoice) {
    return;
  }

  const API = "/api/halo-voice";

  const state = {
    stream: null,
    recorder: null,
    chunks: [],
    recording: false,
  };

  function replyNode() {
    return document.querySelector(
      "#nbHaloReply, [data-halo-reply]"
    );
  }

  function inputNode() {
    return document.querySelector(
      "#nbHaloInput, [data-halo-input]"
    );
  }

  function setStatus(message, mode = "") {
    const reply = replyNode();

    if (reply) {
      reply.textContent = message;
    }

    const status = document.querySelector(
      "#nbUniversalVoiceStatus"
    );

    if (status) {
      status.textContent = message;
      status.dataset.mode = mode;
    }
  }

  function updateButton() {
    const button = document.querySelector(
      "#nbUniversalMic"
    );

    if (!button) {
      return;
    }

    button.innerHTML = state.recording
      ? "<span>■</span><b>Stop</b>"
      : "<span>🎤</span><b>Universal Mic</b>";

    button.setAttribute(
      "aria-pressed",
      String(state.recording)
    );
  }

  async function sendCommand(command) {
    if (
      window.NoorBrainHaloOneClick
      && typeof window.NoorBrainHaloOneClick
        .sendCommand === "function"
    ) {
      await window.NoorBrainHaloOneClick
        .sendCommand(command);
      return;
    }

    const response = await fetch(
      "/api/halo-oneclick/command",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: command,
        }),
      }
    );

    const data = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail
        || `HALO HTTP ${response.status}`
      );
    }

    setStatus(
      data.reply || "Command sent.",
      "done"
    );
  }

  async function uploadRecording(blob) {
    const form = new FormData();
    const type = blob.type || "audio/webm";

    let extension = "webm";

    if (type.includes("ogg")) {
      extension = "ogg";
    } else if (
      type.includes("mp4")
    ) {
      extension = "m4a";
    }

    form.append(
      "audio",
      blob,
      `halo-voice.${extension}`
    );

    const response = await fetch(
      `${API}/transcribe`,
      {
        method: "POST",
        body: form,
      }
    );

    const data = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail
        || `Transcription HTTP ${response.status}`
      );
    }

    return data;
  }

  async function start() {
    if (!window.isSecureContext) {
      throw new Error(
        "Open NoorBrain using HTTPS "
        + "or localhost for microphone access."
      );
    }

    if (
      !navigator.mediaDevices
      || !navigator.mediaDevices.getUserMedia
      || !window.MediaRecorder
    ) {
      throw new Error(
        "This browser cannot record microphone audio."
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

    const supportedTypes = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ];

    const mimeType = supportedTypes.find(
      type => MediaRecorder
        .isTypeSupported(type)
    );

    const recorder = mimeType
      ? new MediaRecorder(
          stream,
          {
            mimeType,
            audioBitsPerSecond: 64000,
          }
        )
      : new MediaRecorder(stream);

    state.stream = stream;
    state.recorder = recorder;
    state.chunks = [];
    state.recording = true;

    recorder.ondataavailable = event => {
      if (
        event.data
        && event.data.size
      ) {
        state.chunks.push(
          event.data
        );
      }
    };

    recorder.onstop = async () => {
      state.recording = false;

      state.stream
        ?.getTracks()
        .forEach(track => track.stop());

      document.body.classList.remove(
        "nb-universal-recording"
      );

      updateButton();

      setStatus(
        "Transcribing locally…",
        "thinking"
      );

      try {
        const blob = new Blob(
          state.chunks,
          {
            type: (
              recorder.mimeType
              || "audio/webm"
            ),
          }
        );

        const result = await uploadRecording(
          blob
        );

        const command = (
          result.command
          || result.text
        ).trim();

        if (!command) {
          throw new Error(
            "No HALO command detected."
          );
        }

        const input = inputNode();

        if (input) {
          input.value = command;
        }

        setStatus(
          `Heard: ${result.text}`,
          "heard"
        );

        await sendCommand(command);
      } catch (error) {
        setStatus(
          error.message,
          "error"
        );
      }
    };

    recorder.start(250);

    document.body.classList.add(
      "nb-universal-recording"
    );

    updateButton();

    setStatus(
      "Listening… speak for 3–8 seconds, "
      + "then tap Stop.",
      "listening"
    );
  }

  function stop() {
    if (
      state.recorder
      && state.recording
    ) {
      state.recorder.stop();
    }
  }

  function toggle() {
    if (state.recording) {
      stop();
      return;
    }

    start().catch(error => {
      setStatus(
        error.message,
        "error"
      );
    });
  }

  function mount() {
    if (
      document.querySelector(
        "#nbUniversalMic"
      )
    ) {
      return;
    }

    const panel = document.createElement(
      "section"
    );

    panel.className =
      "nb-universal-voice-panel";

    panel.innerHTML = `
      <button
        id="nbUniversalMic"
        class="nb-universal-mic"
        type="button"
      >
        <span>🎤</span>
        <b>Universal Mic</b>
      </button>

      <div>
        <strong>
          HALO Universal Voice
        </strong>

        <p id="nbUniversalVoiceStatus">
          Laptop, Raspberry Pi and mobile ready.
        </p>
      </div>
    `;

    const target = document.querySelector(
      ".nb-halo-card, "
      + ".nb-halo-oneclick, "
      + "main, .main, body"
    );

    if (target === document.body) {
      target.prepend(panel);
    } else {
      target.insertAdjacentElement(
        "afterbegin",
        panel
      );
    }

    panel.querySelector(
      "#nbUniversalMic"
    ).addEventListener(
      "click",
      toggle
    );
  }

  window.NoorBrainUniversalVoice = {
    start,
    stop,
    toggle,
  };

  if (
    document.readyState
    === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      mount
    );
  } else {
    mount();
  }
})();
