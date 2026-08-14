"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(
  path.join(__dirname, "../dashboard/js/halo-mic-final-fix.js"),
  "utf8"
);

function harness({native = true, sendHalo, getUserMedia, fetchImpl, nativePlugins} = {}) {
  const messages = [];
  const statuses = [];
  const timers = new Map();
  const listeners = {};
  let timerId = 0;

  const statusNode = {textContent: "", dataset: {}};
  const inputNode = {value: ""};
  const orb = {dataset: {}, setAttribute() {}};
  const prompt = {textContent: ""};
  const body = {classList: {toggle() {}}};
  const document = {
    readyState: "complete",
    body,
    documentElement: {},
    querySelector(selector) {
      if (selector.includes("HaloInput")) return inputNode;
      if (selector.includes("HaloStatus")) return statusNode;
      return null;
    },
    querySelectorAll(selector) {
      if (selector.includes("HaloStatus") || selector.includes("halo-reply")) {
        return [statusNode];
      }
      if (selector.includes("nb126-orb")) return [orb];
      if (selector.includes("nb126-halo-prompt")) return [prompt];
      return [];
    },
    addEventListener() {},
  };

  Object.defineProperty(statusNode, "textContent", {
    get() { return statuses.at(-1) || ""; },
    set(value) { statuses.push(String(value)); },
  });

  class MutationObserver { observe() {} }
  class FakeRecorder {
    static isTypeSupported() { return true; }
    constructor(stream, options = {}) {
      this.stream = stream;
      this.mimeType = options.mimeType || "audio/webm";
      this.state = "inactive";
    }
    start() {
      this.state = "recording";
      this.ondataavailable?.({
        data: new Blob([new Uint8Array(1600)], {type: this.mimeType}),
      });
    }
    stop() {
      this.state = "inactive";
      this.onstop?.();
    }
  }

  const context = {
    console,
    URLSearchParams,
    Blob,
    FormData,
    Date,
    document,
    location: {search: native ? "?native_app=1" : ""},
    navigator: {
      mediaDevices: {
        getUserMedia: getUserMedia || (async () => ({
          getTracks: () => [{stop() {}}],
        })),
      },
    },
    MediaRecorder: FakeRecorder,
    MutationObserver,
    fetch: fetchImpl || (async () => ({
      ok: true,
      json: async () => ({text: "turn on kitchen light", command: "turn on kitchen light"}),
    })),
    isSecureContext: true,
    setTimeout(callback, delay) {
      const id = ++timerId;
      timers.set(id, {callback, delay});
      return id;
    },
    clearTimeout(id) { timers.delete(id); },
    setInterval() { return 1; },
    clearInterval() {},
    addEventListener(type, callback) { listeners[type] = callback; },
    parent: {postMessage(message) { messages.push(message); }},
    Capacitor: nativePlugins ? {Plugins: nativePlugins} : undefined,
    NoorBrainMobile126: {
      sendHalo: sendHalo || (async () => true),
    },
  };
  context.window = context;

  vm.runInNewContext(source, context, {filename: "halo-mic-final-fix.js"});
  const api = context.NoorBrainHaloMicFinalFix;

  return {
    api,
    messages,
    statuses,
    timers,
    async message(data) {
      await listeners.message({data});
    },
    runTimer(delay) {
      const item = [...timers.values()].find(timer => timer.delay === delay);
      assert.ok(item, `expected a ${delay}ms timer`);
      item.callback();
    },
  };
}

async function flush() {
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
}

async function run() {
  let conversations = 0;
  const native = harness({sendHalo: async () => { conversations += 1; }});

  assert.equal(native.api.mode(), "idle");
  await native.api.toggle();
  assert.equal(native.api.mode(), "starting");
  assert.equal(native.messages.length, 1, "first tap starts one native recording");

  await native.api.toggle();
  assert.equal(native.messages.length, 1, "double tap while starting is ignored");

  await native.message({type: "noorbrain-native-listening"});
  assert.equal(native.api.mode(), "listening");
  assert.equal(native.api.isRecording(), true);

  await native.api.toggle();
  assert.equal(native.api.mode(), "stopping");
  assert.equal(native.messages.length, 2, "second tap stops the same recording once");

  await native.api.toggle();
  assert.equal(native.messages.length, 2, "processing taps cannot reactivate the microphone");

  await native.message({type: "noorbrain-native-processing"});
  assert.equal(native.api.mode(), "processing");
  await native.message({type: "noorbrain-native-transcript", text: "What time is Maghrib?"});
  assert.equal(conversations, 1);
  assert.equal(native.api.mode(), "idle");

  await native.message({type: "noorbrain-native-transcript", text: "What time is Maghrib?"});
  assert.equal(conversations, 1, "duplicate transcript cannot send a second conversation");

  const automatic = harness();
  await automatic.api.toggle();
  await automatic.message({type: "noorbrain-native-listening"});
  automatic.runTimer(12000);
  assert.equal(automatic.api.mode(), "stopping");
  assert.equal(automatic.messages.length, 2, "automatic timeout sends one stop, not a start");
  await automatic.message({type: "noorbrain-native-processing"});
  automatic.runTimer(45000);
  assert.equal(automatic.api.mode(), "idle", "lost transcript recovers to idle");
  assert.match(automatic.statuses.at(-1), /timed out/i);

  const permission = harness({
    native: false,
    getUserMedia: async () => { throw new Error("Microphone permission denied."); },
  });
  await permission.api.toggle();
  assert.equal(permission.api.mode(), "idle");
  assert.match(permission.statuses.at(-1), /permission denied/i);

  const transcription = harness({
    native: false,
    fetchImpl: async () => ({
      ok: false,
      status: 503,
      json: async () => ({detail: "Transcription unavailable."}),
    }),
  });
  await transcription.api.toggle();
  assert.equal(transcription.api.mode(), "listening");
  await transcription.api.toggle();
  await flush();
  assert.equal(transcription.api.mode(), "idle");
  assert.match(transcription.statuses.at(-1), /transcription unavailable/i);

  const conversation = harness({
    sendHalo: async () => { throw new Error("Conversation unavailable."); },
  });
  await conversation.api.toggle();
  await conversation.message({type: "noorbrain-native-listening"});
  await conversation.api.toggle();
  await conversation.message({type: "noorbrain-native-processing"});
  await conversation.message({type: "noorbrain-native-transcript", text: "Hello Noor"});
  assert.equal(conversation.api.mode(), "idle");
  assert.match(conversation.statuses.at(-1), /conversation unavailable/i);

  const nativeFailure = harness();
  await nativeFailure.api.toggle();
  await nativeFailure.message({type: "noorbrain-native-error", message: "Recording failed."});
  assert.equal(nativeFailure.api.mode(), "idle");
  assert.match(nativeFailure.statuses.at(-1), /recording failed/i);

  let directStarts = 0;
  let directStops = 0;
  let directConversations = 0;
  const direct = harness({
    nativePlugins: {
      CapacitorAudioRecorder: {
        requestPermissions: async () => ({recordAudio: "granted"}),
        startRecording: async () => { directStarts += 1; },
        stopRecording: async () => {
          directStops += 1;
          return {
            blob: new Blob([new Uint8Array(1600)], {type: "audio/mp4"}),
          };
        },
      },
    },
    sendHalo: async () => { directConversations += 1; },
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({
        text: "Turn on the kitchen light",
        command: "Turn on the kitchen light",
      }),
    }),
  });
  await direct.api.toggle();
  assert.equal(direct.api.mode(), "listening");
  assert.equal(directStarts, 1);
  assert.equal(direct.messages.length, 0, "direct plugin mode does not use parent relay");
  await direct.api.toggle();
  assert.equal(directStops, 1);
  assert.equal(directConversations, 1);
  assert.equal(direct.api.mode(), "idle");
  assert.equal(
    direct.api.diagnostics().map(item => item.event).join(","),
    [
      "MIC_REQUEST",
      "NATIVE_START_SENT",
      "NATIVE_START_ACK",
      "RECORDING_STARTED",
      "STOP_REQUEST",
      "NATIVE_AUDIO_RECEIVED",
      "TRANSCRIBE_START",
      "TRANSCRIBE_RESULT",
      "CHAT_START",
      "CHAT_RESULT",
      "TTS_SENT",
      "VOICE_IDLE",
    ].join(",")
  );

  console.log("HALO voice state machine: PASS");
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
