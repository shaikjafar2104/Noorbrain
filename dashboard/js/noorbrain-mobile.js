cd ~/Projects/NoorBrain

cp dashboard/js/noorbrain-mobile.js \
dashboard/js/noorbrain-mobile.js.backup-$(date +%Y%m%d-%H%M%S)

cat > dashboard/js/noorbrain-mobile.js <<'EOF'
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let deferredPrompt = null;
  let haloBusy = false;

  async function api(path, options = {}) {
    const response = await fetch(path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    const body = await response.json();

    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    return body;
  }

  async function loadStatus() {
    const [mobile, home, voice, diagnostics] = await Promise.allSettled([
      api("/api/mobile-companion/health"),
      api("/api/smart-home-runtime/summary"),
      api("/api/halo-voice-runtime/status"),
      api("/api/release-tools/diagnostics"),
    ]);

    $("mobileStatus").textContent =
      mobile.status === "fulfilled" &&
      mobile.value.status === "healthy"
        ? "Connected"
        : "Limited";

    $("homeSummary").textContent =
      home.status === "fulfilled"
        ? `${home.value.device_count || 0} devices · ${
            home.value.online_devices || 0
          } online`
        : "Unavailable";

    $("voiceSummary").textContent =
      voice.status === "fulfilled"
        ? `Runtime ${voice.value.status || "unknown"}`
        : "Unavailable";

    $("diagnosticsSummary").textContent =
      diagnostics.status === "fulfilled"
        ? diagnostics.value.status
        : "Unavailable";
  }

  async function sendHalo() {
    if (haloBusy) return;

    const text = $("haloText").value.trim();
    if (!text) return;

    haloBusy = true;
    $("sendHalo").disabled = true;
    $("haloResult").textContent = "Thinking…";

    try {
      const result = await api("/api/halo-conversation/chat", {
        method: "POST",
        body: JSON.stringify({
          text,
          session_id: "mobile-companion",
          confirm: false,
        }),
      });

      $("haloResult").textContent =
        result.reply || JSON.stringify(result, null, 2);
    } catch (error) {
      $("haloResult").textContent = `HALO error: ${error.message}`;
    } finally {
      haloBusy = false;
      $("sendHalo").disabled = false;
    }
  }

  function setupSpeech() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    const pushToTalk = $("pushToTalk");

    if (!SpeechRecognition) {
      pushToTalk.disabled = true;
      pushToTalk.textContent = "Mic unsupported";
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      pushToTalk.classList.add("recording");
      pushToTalk.disabled = true;
    };

    recognition.onend = () => {
      pushToTalk.classList.remove("recording");
      pushToTalk.disabled = false;
    };

    recognition.onerror = (event) => {
      $("haloResult").textContent =
        `Microphone error: ${event.error}`;
    };

    recognition.onresult = (event) => {
      $("haloText").value = event.results[0][0].transcript;
      sendHalo();
    };

    pushToTalk.onclick = () => {
      try {
        recognition.abort();
      } catch (_) {}

      try {
        recognition.start();
      } catch (error) {
        console.error("Microphone start failed:", error);
      }
    };
  }

  function setupInstall() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/dashboard-pwa/sw.js")
        .catch(console.error);
    }

    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      deferredPrompt = event;
      $("installApp").hidden = false;
    });

    $("installApp").addEventListener("click", async () => {
      if (!deferredPrompt) return;

      deferredPrompt.prompt();
      await deferredPrompt.userChoice;

      deferredPrompt = null;
      $("installApp").hidden = true;
    });
  }

  $("sendHalo").addEventListener("click", sendHalo);

  document.querySelectorAll("[data-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.target;

      if (target === "top") {
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        $(target)?.focus();
      }
    });
  });

  setupSpeech();
  setupInstall();
  loadStatus();

  setInterval(loadStatus, 30000);
})();
EOF

node --check dashboard/js/noorbrain-mobile.js