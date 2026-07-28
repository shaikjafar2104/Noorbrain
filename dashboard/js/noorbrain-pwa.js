(() => {
  "use strict";

  function installPWA() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/dashboard-pwa/sw.js").catch(console.error);
    }

    if (!document.querySelector('link[rel="manifest"]')) {
      const link = document.createElement("link");
      link.rel = "manifest";
      link.href = "/dashboard-pwa/manifest.webmanifest";
      document.head.appendChild(link);
    }

    let deferredPrompt = null;
    window.addEventListener("beforeinstallprompt", event => {
      event.preventDefault();
      deferredPrompt = event;

      if (document.getElementById("noorbrainInstallApp")) return;

      const button = document.createElement("button");
      button.id = "noorbrainInstallApp";
      button.className = "button secondary";
      button.textContent = "Install App";
      button.style.position = "fixed";
      button.style.right = "18px";
      button.style.bottom = "18px";
      button.style.zIndex = "9999";
      document.body.appendChild(button);

      button.addEventListener("click", async () => {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        await deferredPrompt.userChoice;
        deferredPrompt = null;
        button.remove();
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installPWA);
  } else {
    installPWA();
  }
})();
