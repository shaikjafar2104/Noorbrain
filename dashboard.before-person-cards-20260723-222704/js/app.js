(() => {
  "use strict";

  const state = window.NoorState;
  const api = window.NoorAPI.request;
  const router = window.NoorRouter;

  const {
    $,
    setText,
    bind,
    backendStatus,
    escapeHtml
  } = window.NoorUI;

  // ========================================================
  // Dashboard health
  // ========================================================

  async function refreshHealth() {
    try {
      const data = await api("/health");

      state.health = data;
      backendStatus(true);

      const camera = data.camera || {};
      const vision = data.vision || {};

      setText(
        "cameraStatus",
        camera.connected
          ? "Connected"
          : "Disconnected"
      );

      setText(
        "cameraAge",
        camera.last_frame == null
          ? "No frame"
          : `Last frame ${camera.last_frame}s ago`
      );

      setText(
        "personCount",
        vision.persons ?? 0
      );

      setText(
        "visionFps",
        Number(vision.fps || 0).toFixed(1)
      );

      setText(
        "cameraFps",
        `Camera ${Number(
          camera.fps || 0
        ).toFixed(1)} FPS`
      );

      setText(
        "modelName",
        vision.model || "—"
      );

      setText(
        "confidenceText",
        `Confidence ${Number(
          vision.confidence || 0
        ).toFixed(2)}`
      );

      setText(
        "currentZone",
        vision.persons
          ? "Person detected"
          : "No active person"
      );

      setText(
        "visionStateBadge",
        vision.running
          ? "Running"
          : "Stopped"
      );

      setText(
        "settingsCameraUrl",
        camera.stream_url || "—"
      );

      setText(
        "settingsModel",
        vision.model || "—"
      );

      setText(
        "streamBadge",
        camera.connected
          ? "Live"
          : "Waiting"
      );

      const slider = $("confidenceSlider");
      const confidence =
        Number(vision.confidence || 0);

      if (slider) {
        slider.value = confidence;
      }

      setText(
        "confidenceValue",
        confidence.toFixed(2)
      );
    } catch (error) {
      backendStatus(false);
      setText("cameraStatus", "Offline");

      console.error(
        "Health refresh failed:",
        error
      );
    }
  }

  // ========================================================
  // People
  // ========================================================

  async function loadDetections() {
    try {
      const data = await api("/detections");

      state.detections = Array.isArray(
        data.people
      )
        ? data.people
        : [];

      setText(
        "peopleBadge",
        `${data.count ?? state.detections.length} people`
      );

      const body = $("peopleTable");

      if (!body) {
        return;
      }

      if (!state.detections.length) {
        body.innerHTML = `
          <tr>
            <td colspan="5" class="muted">
              No detections
            </td>
          </tr>
        `;

        return;
      }

      body.innerHTML = state.detections
        .map((person, index) => {
          const personId =
            person.person_id ??
            person.id ??
            index + 1;

          const box = Array.isArray(person.box)
            ? person.box.join(", ")
            : "—";

          return `
            <tr>
              <td>${escapeHtml(personId)}</td>
              <td>
                ${escapeHtml(
                  person.label || "person"
                )}
              </td>
              <td>
                ${escapeHtml(
                  person.zone || "Unknown"
                )}
              </td>
              <td>
                ${Math.round(
                  Number(
                    person.confidence || 0
                  ) * 100
                )}%
              </td>
              <td>${escapeHtml(box)}</td>
            </tr>
          `;
        })
        .join("");
    } catch (error) {
      console.error(
        "Detections load failed:",
        error
      );
    }
  }

  // ========================================================
  // Timeline events
  // ========================================================

  function describeEvent(event) {
    if (event.event === "entered") {
      return `Person entered ${event.zone}`;
    }

    if (event.event === "left") {
      return `Person left ${event.zone}`;
    }

    if (event.event === "moved") {
      return (
        `Person moved ${event.source} → ` +
        `${event.destination}`
      );
    }

    return (
      event.message ||
      event.event ||
      event.type ||
      "Activity event"
    );
  }

  async function loadEvents() {
    try {
      const data = await api(
        "/events?limit=100"
      );

      state.events = Array.isArray(data.events)
        ? data.events
        : [];

      const timeline = $("timelineList");

      if (timeline) {
        timeline.innerHTML = state.events.length
          ? state.events
              .map(event => {
                const timestamp =
                  event.time ??
                  event.timestamp ??
                  Date.now() / 1000;

                return `
                  <div class="timeline-item">
                    <strong>
                      ${escapeHtml(
                        describeEvent(event)
                      )}
                    </strong>

                    <time>
                      ${new Date(
                        timestamp * 1000
                      ).toLocaleString()}
                    </time>
                  </div>
                `;
              })
              .join("")
          : "No stored events.";

        timeline.classList.toggle(
          "empty",
          !state.events.length
        );
      }

      const recent = $("recentEvents");

      if (recent) {
        recent.innerHTML = state.events.length
          ? state.events
              .slice(0, 7)
              .map(event => {
                const timestamp =
                  event.time ??
                  event.timestamp ??
                  Date.now() / 1000;

                return `
                  <div class="event">
                    <strong>
                      ${escapeHtml(
                        describeEvent(event)
                      )}
                    </strong>

                    <time>
                      ${new Date(
                        timestamp * 1000
                      ).toLocaleTimeString()}
                    </time>
                  </div>
                `;
              })
              .join("")
          : "No events yet.";
      }
    } catch (error) {
      console.error(
        "Events load failed:",
        error
      );
    }
  }

  // ========================================================
  // Vision controls
  // ========================================================

  async function runAction(action) {
    const message = $("actionMessage");

    if (message) {
      message.textContent = "Working…";
    }

    const paths = {
      "vision-start":
        "/control/vision/start",

      "vision-stop":
        "/control/vision/stop",

      "vision-restart":
        "/control/vision/restart",

      "camera-reconnect":
        "/control/camera/reconnect"
    };

    const path = paths[action];

    if (!path) {
      return;
    }

    try {
      const data = await api(
        path,
        {
          method: "POST"
        }
      );

      if (message) {
        message.textContent =
          data.message || "Done";
      }

      setTimeout(
        refreshHealth,
        600
      );
    } catch (error) {
      if (message) {
        message.textContent = error.message;
      }
    }
  }

  document.addEventListener(
    "click",
    event => {
      const actionButton =
        event.target.closest("[data-action]");

      if (
        actionButton &&
        actionButton.dataset.action
      ) {
        runAction(
          actionButton.dataset.action
        );
      }
    }
  );

  // ========================================================
  // HALO
  // ========================================================

  async function submitHalo(event) {
    event.preventDefault();

    const input = $("haloInput");
    const box = $("chatMessages");

    if (!input || !box) {
      return;
    }

    const question = input.value.trim();

    if (!question) {
      return;
    }

    const userBubble =
      document.createElement("div");

    userBubble.className = "bubble user";
    userBubble.textContent = question;
    box.appendChild(userBubble);

    input.value = "";
    setText("haloBadge", "Thinking…");

    try {
      const data = await api(
        "/halo",
        {
          method: "POST",
          body: JSON.stringify({
            message: question
          })
        }
      );

      const answerBubble =
        document.createElement("div");

      answerBubble.className =
        "bubble assistant";

      answerBubble.textContent =
        data.reply || "No reply.";

      box.appendChild(answerBubble);

      setText("haloBadge", "Ready");
    } catch (error) {
      const errorBubble =
        document.createElement("div");

      errorBubble.className =
        "bubble assistant";

      errorBubble.textContent =
        `HALO error: ${error.message}`;

      box.appendChild(errorBubble);

      setText("haloBadge", "Error");
    }

    box.scrollTop = box.scrollHeight;
  }

  bind(
    "haloForm",
    "submit",
    submitHalo
  );

  // ========================================================
  // Settings
  // ========================================================

  bind(
    "confidenceSlider",
    "input",
    event => {
      setText(
        "confidenceValue",
        Number(
          event.target.value
        ).toFixed(2)
      );
    }
  );

  bind(
    "saveSettingsBtn",
    "click",
    async () => {
      const slider =
        $("confidenceSlider");

      if (!slider) {
        return;
      }

      const confidence =
        Number(slider.value);

      try {
        const data = await api(
          "/settings/vision",
          {
            method: "POST",
            body: JSON.stringify({
              confidence
            })
          }
        );

        setText(
          "settingsMessage",
          data.message ||
          "Settings saved."
        );
      } catch (error) {
        setText(
          "settingsMessage",
          error.message
        );
      }
    }
  );

  // ========================================================
  // Zones
  // ========================================================

  async function loadZones() {
    try {
      const [zoneData, sizeData] =
        await Promise.all([
          api("/zones"),
          api("/frame_size")
        ]);

      state.zones = Array.isArray(
        zoneData.zones
      )
        ? zoneData.zones
        : (
            Array.isArray(zoneData)
              ? zoneData
              : []
          );

      state.frameSize = {
        width:
          Number(sizeData.width) || 1280,

        height:
          Number(sizeData.height) || 720
      };

      renderZoneList();
      setupZoneCanvas();
    } catch (error) {
      console.error(
        "Zones load failed:",
        error
      );
    }
  }

  function renderZoneList() {
    const box = $("zoneList");

    if (!box) {
      return;
    }

    if (!state.zones.length) {
      box.innerHTML =
        "No zones configured.";

      box.classList.add("empty");
      return;
    }

    box.classList.remove("empty");

    box.innerHTML = state.zones
      .map((zone, index) => `
        <div class="zone-row">
          <span>
            <strong>
              ${escapeHtml(zone.name)}
            </strong>

            <br>

            <small>
              ${zone.x1},${zone.y1}
              →
              ${zone.x2},${zone.y2}
            </small>
          </span>

          <button
            class="button danger"
            data-zone-delete="${index}"
          >
            Delete
          </button>
        </div>
      `)
      .join("");
  }

  function setupZoneCanvas() {
    const image = $("zoneVideo");
    const canvas = $("zoneCanvas");

    if (!image || !canvas) {
      return;
    }

    const resize = () => {
      canvas.width = image.clientWidth;
      canvas.height = image.clientHeight;
      drawZones();
    };

    if (image.complete) {
      resize();
    }

    image.onload = resize;

    window.addEventListener(
      "resize",
      resize,
      {
        once: true
      }
    );

    canvas.onmousedown = event => {
      const rectangle =
        canvas.getBoundingClientRect();

      state.drawing = true;

      state.startX =
        event.clientX - rectangle.left;

      state.startY =
        event.clientY - rectangle.top;
    };

    canvas.onmousemove = event => {
      if (!state.drawing) {
        return;
      }

      const rectangle =
        canvas.getBoundingClientRect();

      const x =
        event.clientX - rectangle.left;

      const y =
        event.clientY - rectangle.top;

      state.temp = {
        name: "New zone",

        x1: Math.min(state.startX, x),
        y1: Math.min(state.startY, y),
        x2: Math.max(state.startX, x),
        y2: Math.max(state.startY, y),

        display: true
      };

      drawZones();
    };

    canvas.onmouseup = () => {
      if (
        !state.drawing ||
        !state.temp
      ) {
        return;
      }

      state.drawing = false;

      const name = prompt(
        "Zone name:",
        "New Zone"
      );

      if (name && name.trim()) {
        const scaleX =
          state.frameSize.width /
          canvas.width;

        const scaleY =
          state.frameSize.height /
          canvas.height;

        state.zones.push({
          name: name.trim(),

          x1: Math.round(
            state.temp.x1 * scaleX
          ),

          y1: Math.round(
            state.temp.y1 * scaleY
          ),

          x2: Math.round(
            state.temp.x2 * scaleX
          ),

          y2: Math.round(
            state.temp.y2 * scaleY
          )
        });
      }

      state.temp = null;

      renderZoneList();
      drawZones();
    };
  }

  function drawZones() {
    const canvas = $("zoneCanvas");

    if (!canvas) {
      return;
    }

    const context =
      canvas.getContext("2d");

    context.clearRect(
      0,
      0,
      canvas.width,
      canvas.height
    );

    const scaleX =
      canvas.width /
      state.frameSize.width;

    const scaleY =
      canvas.height /
      state.frameSize.height;

    for (const zone of state.zones) {
      context.strokeStyle = "#ffbd59";
      context.lineWidth = 2;

      context.strokeRect(
        zone.x1 * scaleX,
        zone.y1 * scaleY,
        (zone.x2 - zone.x1) * scaleX,
        (zone.y2 - zone.y1) * scaleY
      );

      context.fillStyle = "#ffbd59";
      context.font = "15px sans-serif";

      context.fillText(
        zone.name,
        zone.x1 * scaleX + 6,
        zone.y1 * scaleY + 19
      );
    }

    if (state.temp) {
      context.strokeStyle = "#22d3a0";

      context.strokeRect(
        state.temp.x1,
        state.temp.y1,
        state.temp.x2 - state.temp.x1,
        state.temp.y2 - state.temp.y1
      );
    }
  }

  document.addEventListener(
    "click",
    event => {
      const deleteButton =
        event.target.closest(
          "[data-zone-delete]"
        );

      if (!deleteButton) {
        return;
      }

      const index = Number(
        deleteButton.dataset.zoneDelete
      );

      if (
        Number.isInteger(index) &&
        state.zones[index]
      ) {
        state.zones.splice(index, 1);
        renderZoneList();
        drawZones();
      }
    }
  );

  bind(
    "saveZonesBtn",
    "click",
    async () => {
      try {
        await api(
          "/zones/save",
          {
            method: "POST",
            body: JSON.stringify(
              state.zones
            )
          }
        );

        alert("Zones saved.");
      } catch (error) {
        alert(error.message);
      }
    }
  );

  bind(
    "clearZonesBtn",
    "click",
    () => {
      if (!confirm("Clear all zones?")) {
        return;
      }

      state.zones = [];
      renderZoneList();
      drawZones();
    }
  );

  bind(
    "reloadZonesBtn",
    "click",
    loadZones
  );

  bind(
    "timelineRefresh",
    "click",
    loadEvents
  );

  bind(
    "refreshBtn",
    "click",
    () => Promise.all([
      refreshHealth(),
      loadDetections(),
      loadEvents()
    ])
  );

  // ========================================================
  // Camera stream recovery
  // ========================================================

  function recoverStreams() {
    document
      .querySelectorAll("[data-stream]")
      .forEach(image => {
        image.onerror = () => {
          setTimeout(
            () => {
              image.src =
                `/vision_feed?retry=${Date.now()}`;
            },
            1500
          );
        };
      });
  }

  // ========================================================
  // Register existing pages
  // ========================================================

  router.register(
    "dashboard",
    {
      title: "Dashboard",
      subtitle: "Live NoorBrain status",

      onOpen() {
        refreshHealth();
        loadEvents();
      }
    }
  );

  router.register(
    "vision",
    {
      title: "Vision",
      subtitle:
        "Camera stream and vision controls",

      onOpen() {
        refreshHealth();
      }
    }
  );

  router.register(
    "people",
    {
      title: "People",
      subtitle:
        "Current YOLO detections",

      onOpen() {
        loadDetections();
      }
    }
  );

  router.register(
    "zones",
    {
      title: "Zones",
      subtitle:
        "Draw and manage camera zones",

      onOpen() {
        loadZones();

        setTimeout(
          setupZoneCanvas,
          250
        );
      }
    }
  );

  router.register(
    "timeline",
    {
      title: "Timeline",
      subtitle:
        "Stored movement events",

      onOpen() {
        loadEvents();
      }
    }
  );

  router.register(
    "halo",
    {
      title: "HALO",
      subtitle:
        "Chat with NoorBrain"
    }
  );

  router.register(
    "settings",
    {
      title: "Settings",
      subtitle:
        "Vision and system configuration",

      onOpen() {
        refreshHealth();
      }
    }
  );

  // ========================================================
  // Startup
  // ========================================================

  function start() {
    router.initialize("dashboard");

    recoverStreams();

    refreshHealth();
    loadDetections();
    loadEvents();
    loadZones();

    setInterval(
      () => {
        setText(
          "clock",
          new Date().toLocaleTimeString()
        );
      },
      1000
    );

    setInterval(
      refreshHealth,
      1500
    );

    setInterval(
      loadDetections,
      2000
    );

    setInterval(
      loadEvents,
      10000
    );
  }

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      start
    );
  } else {
    start();
  }

  window.NoorApp = {
    refreshHealth,
    loadDetections,
    loadEvents,
    loadZones,
    showPage: router.show
  };
})();
