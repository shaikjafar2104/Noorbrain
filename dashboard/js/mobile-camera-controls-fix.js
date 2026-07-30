(() => {
  "use strict";

  if (window.NoorBrainMobileCameraControlsFix) return;

  const VERSION = "1.0.0";

  const cameraCandidates = [
    "/video_feed",
    "/api/vision/video_feed",
    "/api/vision/stream",
    "/api/camera/video_feed",
    "/camera/video_feed",
    "/stream",
  ];

  const state = {
    cameraUrl: "",
    cameraReady: false,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(message, mode = "") {
    const node = byId("nbMobileCameraStatus");
    if (!node) return;

    node.textContent = message;
    node.dataset.mode = mode;
  }

  function cacheBust(url) {
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}v=${Date.now()}`;
  }

  function testImage(url) {
    return new Promise(resolve => {
      const image = new Image();
      let finished = false;

      const done = result => {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        image.onload = null;
        image.onerror = null;
        resolve(result);
      };

      image.onload = () => done(true);
      image.onerror = () => done(false);

      const timer = setTimeout(
        () => done(false),
        3500
      );

      image.src = cacheBust(url);
    });
  }

  async function detectCamera() {
    setStatus(
      "Finding NoorBrain camera…",
      "loading"
    );

    for (const url of cameraCandidates) {
      const ok = await testImage(url);

      if (ok) {
        state.cameraUrl = url;
        state.cameraReady = true;
        showCamera(url);
        setStatus(
          "Camera live",
          "success"
        );
        return true;
      }
    }

    state.cameraReady = false;
    showCameraUnavailable();

    setStatus(
      "Camera stream not found. Open Vision Studio to verify camera service.",
      "error"
    );

    return false;
  }

  function showCamera(url) {
    const image = byId(
      "nbMobileCameraFeed"
    );

    const placeholder = byId(
      "nbMobileCameraPlaceholder"
    );

    if (!image) return;

    image.src = cacheBust(url);
    image.hidden = false;

    if (placeholder) {
      placeholder.hidden = true;
    }
  }

  function showCameraUnavailable() {
    const image = byId(
      "nbMobileCameraFeed"
    );

    const placeholder = byId(
      "nbMobileCameraPlaceholder"
    );

    if (image) {
      image.hidden = true;
      image.removeAttribute("src");
    }

    if (placeholder) {
      placeholder.hidden = false;
    }
  }

  function refreshCamera() {
    if (!state.cameraUrl) {
      detectCamera();
      return;
    }

    const image = byId(
      "nbMobileCameraFeed"
    );

    if (image) {
      image.src = cacheBust(
        state.cameraUrl
      );
    }

    setStatus(
      "Camera refreshed",
      "success"
    );
  }

  async function fullscreenCamera() {
    const shell = byId(
      "nbMobileCameraShell"
    );

    if (!shell) return;

    try {
      if (!document.fullscreenElement) {
        await shell.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (_) {
      shell.classList.toggle(
        "nb-camera-expanded"
      );
    }
  }

  function snapshot() {
    const image = byId(
      "nbMobileCameraFeed"
    );

    if (
      !image
      || image.hidden
      || !image.src
    ) {
      setStatus(
        "Camera is not ready.",
        "error"
      );
      return;
    }

    const canvas =
      document.createElement("canvas");

    const width =
      image.naturalWidth || 1280;

    const height =
      image.naturalHeight || 720;

    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext(
      "2d"
    );

    try {
      context.drawImage(
        image,
        0,
        0,
        width,
        height
      );

      const link =
        document.createElement("a");

      link.download =
        `noorbrain-camera-${Date.now()}.png`;

      link.href =
        canvas.toDataURL("image/png");

      link.click();

      setStatus(
        "Snapshot saved",
        "success"
      );
    } catch (_) {
      window.open(
        image.src,
        "_blank",
        "noopener"
      );
    }
  }

  function openStudio() {
    window.location.href =
      "/studio#vision";
  }

  function openAddDevice() {
    if (
      window.NoorBrainHaloOneClick
      && typeof window.NoorBrainHaloOneClick
        .openDeviceModal === "function"
    ) {
      window.NoorBrainHaloOneClick
        .openDeviceModal();
      return;
    }

    document.querySelector(
      "#nbAddDevice, "
      + "#nbMobileAddFirstDevice"
    )?.click();
  }

  function talkToHalo() {
    document.querySelector(
      "#nbUniversalMic, "
      + "#nbHaloMic, "
      + "[data-nb-final-mic='true']"
    )?.click();
  }

  function showSection(selector) {
    const target =
      document.querySelector(selector);

    if (!target) return;

    target.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  function handleAction(action) {
    const handlers = {
      home: () => window.scrollTo({
        top: 0,
        behavior: "smooth",
      }),
      devices: openAddDevice,
      halo: talkToHalo,
      vision: () => showSection(
        "#nbMobileCameraCard"
      ),
      more: () => showSection(
        ".nb-mobile-essential-grid"
      ),
      cameraRefresh: refreshCamera,
      cameraFullscreen: fullscreenCamera,
      cameraSnapshot: snapshot,
      cameraStudio: openStudio,
    };

    handlers[action]?.();
  }

  function repairClicks() {
    document.querySelectorAll(
      "[data-action], "
      + "[data-mobile-tab], "
      + "#nbMobileRefreshDevices"
    ).forEach(button => {
      button.style.pointerEvents = "auto";
      button.style.position =
        button.style.position || "relative";

      button.style.zIndex = "5";
    });

    document.querySelectorAll(
      ".nb-mobile-home-center, "
      + ".nb-mobile-home-nav, "
      + ".nb-mobile-section, "
      + ".nb-mobile-hero"
    ).forEach(element => {
      element.style.pointerEvents = "auto";
    });
  }

  function mountCamera() {
    if (byId("nbMobileCameraCard")) return;

    const card =
      document.createElement("section");

    card.id = "nbMobileCameraCard";
    card.className =
      "nb-mobile-camera-card";

    card.innerHTML = `
      <div class="nb-mobile-camera-head">
        <div>
          <span>LIVE HOME</span>
          <h2>Camera</h2>
          <p id="nbMobileCameraStatus">
            Connecting…
          </p>
        </div>

        <button
          type="button"
          data-nb-camera-action="cameraRefresh"
        >
          ↻ Refresh
        </button>
      </div>

      <div
        id="nbMobileCameraShell"
        class="nb-mobile-camera-shell"
      >
        <img
          id="nbMobileCameraFeed"
          alt="NoorBrain live camera"
          hidden
        >

        <div
          id="nbMobileCameraPlaceholder"
          class="nb-mobile-camera-placeholder"
        >
          <span>📷</span>
          <b>Camera unavailable</b>
          <small>
            Verify Vision AI or Camera Service.
          </small>
        </div>

        <div class="nb-mobile-camera-live">
          <i></i>
          LIVE
        </div>
      </div>

      <div class="nb-mobile-camera-actions">
        <button
          type="button"
          data-nb-camera-action="cameraFullscreen"
        >
          ⛶ Full Screen
        </button>

        <button
          type="button"
          data-nb-camera-action="cameraSnapshot"
        >
          ◉ Snapshot
        </button>

        <button
          type="button"
          data-nb-camera-action="cameraStudio"
        >
          ⚙ Controls
        </button>
      </div>
    `;

    const home =
      byId("nbMobileHomeCenter");

    const hero =
      home?.querySelector(
        ".nb-mobile-hero"
      );

    if (hero) {
      hero.insertAdjacentElement(
        "afterend",
        card
      );
    } else if (home) {
      home.prepend(card);
    } else {
      document.body.prepend(card);
    }

    card.querySelectorAll(
      "[data-nb-camera-action]"
    ).forEach(button => {
      button.addEventListener(
        "click",
        event => {
          event.preventDefault();
          event.stopPropagation();

          handleAction(
            button.dataset.nbCameraAction
          );
        }
      );
    });

    detectCamera();
  }

  function patchNavigation() {
    document.addEventListener(
      "click",
      event => {
        const button =
          event.target.closest(
            ".nb-mobile-home-nav button"
          );

        if (!button) return;

        event.preventDefault();
        event.stopPropagation();

        const action =
          button.dataset.action
          || button.dataset.mobileTab;

        document.querySelectorAll(
          ".nb-mobile-home-nav button"
        ).forEach(item => {
          item.classList.remove(
            "is-active"
          );
        });

        button.classList.add(
          "is-active"
        );

        handleAction(action);
      },
      true
    );

    document.addEventListener(
      "click",
      event => {
        const button =
          event.target.closest(
            "[data-action='camera']"
          );

        if (!button) return;

        event.preventDefault();
        event.stopPropagation();

        handleAction("vision");
      },
      true
    );
  }

  function install() {
    mountCamera();
    repairClicks();
    patchNavigation();

    const observer =
      new MutationObserver(() => {
        repairClicks();

        if (
          !byId("nbMobileCameraCard")
        ) {
          mountCamera();
        }
      });

    observer.observe(
      document.body,
      {
        subtree: true,
        childList: true,
      }
    );

    window.NoorBrainMobileCameraControlsFix = {
      version: VERSION,
      detectCamera,
      refreshCamera,
      fullscreenCamera,
      snapshot,
      repairClicks,
    };
  }

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      install
    );
  } else {
    install();
  }
})();
