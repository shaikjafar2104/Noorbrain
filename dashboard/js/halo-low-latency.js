(() => {
  "use strict";
  if (window.NoorBrainHaloLowLatency) return;

  const API = "/api/halo-voice";
  let warmed = false;

  function setStatus(message, mode = "") {
    document.querySelectorAll(
      "#nbUniversalVoiceStatus, #nbHaloReply, [data-halo-reply]"
    ).forEach(node => {
      node.textContent = message;
      node.dataset.voiceMode = mode;
    });
  }

  async function warmup() {
    if (warmed) return;
    setStatus("Preparing fast local voice…", "thinking");

    try {
      const response = await fetch(`${API}/warmup`, {
        method: "POST",
        cache: "no-store"
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Warmup HTTP ${response.status}`);
      warmed = true;
      setStatus("HALO voice ready. Tap and speak for 2–4 seconds.", "ready");
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  function patchText() {
    const observer = new MutationObserver(() => {
      document.querySelectorAll(
        "#nbUniversalVoiceStatus, #nbHaloReply, [data-halo-reply]"
      ).forEach(node => {
        if (node.textContent.includes("3–8 seconds")) {
          node.textContent = node.textContent.replace("3–8 seconds", "2–4 seconds");
        }
      });
    });
    observer.observe(document.body, {subtree:true, childList:true, characterData:true});
  }

  function install() {
    patchText();
    warmup();
    window.NoorBrainHaloLowLatency = {warmup, version:"3.1.0"};
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install);
  } else {
    install();
  }
})();
