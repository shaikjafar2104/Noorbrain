(() => {
  "use strict";

  const API = window.location.origin;

  let mediaItems = [];
  let categories = [];
  let initialized = false;

  const $ = id => document.getElementById(id);

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function addStyles() {
    if ($("mediaLibraryStyles")) {
      return;
    }

    const style = document.createElement("style");
    style.id = "mediaLibraryStyles";

    style.textContent = `
      .ml-layout {
        display:grid;
        grid-template-columns:
          minmax(310px, 410px) 1fr;
        gap:18px;
      }

      .ml-form {
        display:grid;
        gap:14px;
      }

      .ml-form label {
        display:grid;
        gap:7px;
        font-size:.9rem;
        font-weight:650;
      }

      .ml-form input,
      .ml-form select,
      .ml-toolbar input,
      .ml-toolbar select {
        width:100%;
        box-sizing:border-box;
        padding:11px 12px;
        border-radius:9px;
        border:1px solid var(--line);
        background:#0e1218;
        color:var(--text);
      }

      .ml-file-input {
        padding:10px !important;
      }

      .ml-toolbar {
        display:grid;
        grid-template-columns:
          minmax(180px, 1fr)
          minmax(150px, 220px)
          auto;
        gap:10px;
        margin-bottom:15px;
      }

      .ml-actions {
        display:flex;
        gap:8px;
        flex-wrap:wrap;
      }

      .ml-message {
        min-height:22px;
        padding:9px 0;
        color:var(--muted);
        font-size:.86rem;
      }

      .ml-message.success {
        color:var(--green);
      }

      .ml-message.error {
        color:var(--red);
      }

      .ml-status-grid {
        display:grid;
        grid-template-columns:repeat(3, 1fr);
        gap:10px;
        margin-top:18px;
      }

      .ml-status-box {
        padding:13px;
        background:var(--panel2);
        border:1px solid var(--line);
        border-radius:10px;
      }

      .ml-status-box span {
        display:block;
        color:var(--muted);
        font-size:.76rem;
      }

      .ml-status-box strong {
        display:block;
        margin-top:5px;
        font-size:1rem;
      }

      .ml-name {
        display:flex;
        flex-direction:column;
        gap:4px;
      }

      .ml-name small {
        color:var(--muted);
        word-break:break-all;
      }

      .ml-category {
        display:inline-flex;
        padding:5px 9px;
        border-radius:999px;
        background:#24302e;
        color:var(--green);
        font-size:.76rem;
      }

      .ml-empty {
        text-align:center;
        padding:38px 15px;
        color:var(--muted);
      }

      .ml-table button {
        padding:8px 10px;
      }

      .ml-progress {
        display:none;
        margin-top:8px;
        color:var(--amber);
        font-size:.85rem;
      }

      .ml-progress.visible {
        display:block;
      }

      @media(max-width:1000px) {
        .ml-layout {
          grid-template-columns:1fr;
        }
      }

      @media(max-width:700px) {
        .ml-toolbar {
          grid-template-columns:1fr;
        }

        .ml-status-grid {
          grid-template-columns:1fr;
        }

        .ml-table thead {
          display:none;
        }

        .ml-table,
        .ml-table tbody,
        .ml-table tr,
        .ml-table td {
          display:block;
          width:100%;
        }

        .ml-table tr {
          padding:12px 0;
          border-bottom:1px solid var(--line);
        }

        .ml-table td {
          border:0;
          padding:7px 5px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function buildPage() {
    addStyles();

    const nav = $("nav");

    if (
      nav &&
      !nav.querySelector('[data-page="media-library"]')
    ) {
      const button = document.createElement("button");

      button.className = "nav-item";
      button.dataset.page = "media-library";
      button.innerHTML =
        "🎵 <span>Media Library</span>";

      const reminderButton =
        nav.querySelector(
          '[data-page="reminder-rules"]'
        );

      const settingsButton =
        nav.querySelector(
          '[data-page="settings"]'
        );

      if (reminderButton) {
        reminderButton.insertAdjacentElement(
          "afterend",
          button
        );
      } else if (settingsButton) {
        nav.insertBefore(button, settingsButton);
      } else {
        nav.appendChild(button);
      }
    }

    if ($("page-media-library")) {
      return;
    }

    const main = document.querySelector("main.main");

    if (!main) {
      console.error(
        "Media Library: dashboard main element missing"
      );
      return;
    }

    const section = document.createElement("section");

    section.id = "page-media-library";
    section.className = "page";

    section.innerHTML = `
      <div class="ml-layout">

        <article class="card">
          <div class="card-head">
            <div>
              <h2>Upload Audio</h2>
              <p>
                Add Duas, Azkar, alerts and
                custom reminder sounds.
              </p>
            </div>
          </div>

          <form id="mlUploadForm" class="ml-form">
            <label>
              Audio file
              <input
                id="mlFile"
                class="ml-file-input"
                type="file"
                accept=".mp3,.wav,.ogg,.m4a,.aac,.flac,audio/*"
                required
              >
            </label>

            <label>
              Display name
              <input
                id="mlDisplayName"
                type="text"
                placeholder="Example: Entering home Dua"
              >
            </label>

            <label>
              Category
              <select id="mlUploadCategory">
                <option value="Islamic">Islamic</option>
                <option value="Azkar">Azkar</option>
                <option value="Dua">Dua</option>
                <option value="Prayer">Prayer</option>
                <option value="Alerts">Alerts</option>
                <option value="Personal">Personal</option>
                <option value="Custom">Custom</option>
              </select>
            </label>

            <button
              id="mlUploadButton"
              class="button success"
              type="submit"
            >
              Upload Audio
            </button>

            <div
              id="mlProgress"
              class="ml-progress"
            >
              Uploading audio…
            </div>

            <div
              id="mlMessage"
              class="ml-message"
            ></div>
          </form>

          <div class="ml-status-grid">
            <div class="ml-status-box">
              <span>Total media</span>
              <strong id="mlTotalCount">0</strong>
            </div>

            <div class="ml-status-box">
              <span>Playback</span>
              <strong id="mlPlaybackStatus">
                Stopped
              </strong>
            </div>

            <div class="ml-status-box">
              <span>Categories</span>
              <strong id="mlCategoryCount">0</strong>
            </div>
          </div>
        </article>

        <article class="card">
          <div class="card-head">
            <div>
              <h2>Audio Files</h2>
              <p>
                Search, preview and manage
                NoorBrain media.
              </p>
            </div>
          </div>

          <div class="ml-toolbar">
            <input
              id="mlSearch"
              type="search"
              placeholder="Search audio…"
            >

            <select id="mlCategoryFilter">
              <option value="">All categories</option>
            </select>

            <button
              id="mlRefresh"
              class="button secondary"
              type="button"
            >
              Refresh
            </button>
          </div>

          <div class="table-wrap">
            <table class="ml-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Size</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody id="mlTableBody">
                <tr>
                  <td colspan="4" class="ml-empty">
                    Loading media library…
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

      </div>
    `;

    main.appendChild(section);
  }

  async function request(path, options = {}) {
    const response = await fetch(
      API + path,
      {
        cache: "no-store",
        ...options
      }
    );

    const contentType =
      response.headers.get("content-type") || "";

    let body;

    if (contentType.includes("application/json")) {
      body = await response.json();
    } else {
      body = await response.text();
    }

    if (!response.ok) {
      const detail =
        typeof body === "object"
          ? body.detail ||
            body.message ||
            JSON.stringify(body)
          : body;

      throw new Error(
        detail || `HTTP ${response.status}`
      );
    }

    return body;
  }

  function normalizeItems(data) {
    if (Array.isArray(data)) {
      return data;
    }

    const possibleLists = [
      data?.items,
      data?.media,
      data?.files,
      data?.audio,
      data?.results
    ];

    return (
      possibleLists.find(Array.isArray) || []
    );
  }

  function normalizeCategories(data) {
    if (Array.isArray(data)) {
      return data;
    }

    if (Array.isArray(data?.categories)) {
      return data.categories;
    }

    return [];
  }

  function itemId(item) {
    return (
      item.id ??
      item.media_id ??
      item.uuid ??
      item.key ??
      item.filename
    );
  }

  function itemName(item) {
    return (
      item.display_name ||
      item.name ||
      item.title ||
      item.original_filename ||
      item.filename ||
      "Unnamed audio"
    );
  }

  function itemFilename(item) {
    return (
      item.original_filename ||
      item.filename ||
      item.file_name ||
      item.path ||
      ""
    );
  }

  function itemCategory(item) {
    return (
      item.category ||
      item.group ||
      "Custom"
    );
  }

  function itemSize(item) {
    const bytes = Number(
      item.size ??
      item.size_bytes ??
      item.file_size ??
      0
    );

    if (!bytes) {
      return "—";
    }

    if (bytes < 1024) {
      return `${bytes} B`;
    }

    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return (
      `${(
        bytes /
        (1024 * 1024)
      ).toFixed(1)} MB`
    );
  }

  function setMessage(message, type = "") {
    const element = $("mlMessage");

    if (!element) {
      return;
    }

    element.textContent = message;
    element.className =
      `ml-message ${type}`.trim();
  }

  function renderCategoryOptions() {
    const uploadSelect = $("mlUploadCategory");
    const filterSelect = $("mlCategoryFilter");

    const builtIn = [
      "Islamic",
      "Azkar",
      "Dua",
      "Prayer",
      "Alerts",
      "Personal",
      "Custom"
    ];

    const discovered = mediaItems
      .map(itemCategory)
      .filter(Boolean);

    categories = [
      ...new Set([
        ...builtIn,
        ...categories,
        ...discovered
      ])
    ];

    if (uploadSelect) {
      const current =
        uploadSelect.value || "Islamic";

      uploadSelect.innerHTML = categories
        .map(category => `
          <option value="${escapeHtml(category)}">
            ${escapeHtml(category)}
          </option>
        `)
        .join("");

      if (categories.includes(current)) {
        uploadSelect.value = current;
      }
    }

    if (filterSelect) {
      const current = filterSelect.value;

      filterSelect.innerHTML = `
        <option value="">All categories</option>
        ${categories
          .map(category => `
            <option value="${escapeHtml(category)}">
              ${escapeHtml(category)}
            </option>
          `)
          .join("")}
      `;

      if (categories.includes(current)) {
        filterSelect.value = current;
      }
    }

    const count = $("mlCategoryCount");

    if (count) {
      count.textContent = categories.length;
    }
  }

  function filteredItems() {
    const query =
      ($("mlSearch")?.value || "")
        .trim()
        .toLowerCase();

    const selectedCategory =
      $("mlCategoryFilter")?.value || "";

    return mediaItems.filter(item => {
      const searchText = [
        itemName(item),
        itemFilename(item),
        itemCategory(item)
      ]
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !query || searchText.includes(query);

      const matchesCategory =
        !selectedCategory ||
        itemCategory(item) === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }

  function renderItems() {
    const body = $("mlTableBody");

    if (!body) {
      return;
    }

    const items = filteredItems();

    if (!items.length) {
      body.innerHTML = `
        <tr>
          <td colspan="4" class="ml-empty">
            ${
              mediaItems.length
                ? "No matching audio found."
                : "No audio uploaded yet."
            }
          </td>
        </tr>
      `;

      return;
    }

    body.innerHTML = items
      .map(item => {
        const id = String(itemId(item) ?? "");
        const name = itemName(item);
        const filename = itemFilename(item);
        const category = itemCategory(item);

        return `
          <tr>
            <td>
              <div class="ml-name">
                <strong>${escapeHtml(name)}</strong>
                <small>${escapeHtml(filename)}</small>
              </div>
            </td>

            <td>
              <span class="ml-category">
                ${escapeHtml(category)}
              </span>
            </td>

            <td>${escapeHtml(itemSize(item))}</td>

            <td>
              <div class="ml-actions">
                <button
                  class="button success"
                  type="button"
                  data-ml-action="play"
                  data-media-id="${escapeHtml(id)}"
                >
                  ▶ Play
                </button>

                <button
                  class="button secondary"
                  type="button"
                  data-ml-action="stop"
                >
                  ■ Stop
                </button>

                <button
                  class="button danger"
                  type="button"
                  data-ml-action="delete"
                  data-media-id="${escapeHtml(id)}"
                  data-media-name="${escapeHtml(name)}"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  async function loadStatus() {
    try {
      const data = await request("/media/status");

      const total =
        data.total_items ??
        data.total ??
        data.count ??
        mediaItems.length;

      const playing =
        data.playing ??
        data.is_playing ??
        false;

      if ($("mlTotalCount")) {
        $("mlTotalCount").textContent = total;
      }

      if ($("mlPlaybackStatus")) {
        $("mlPlaybackStatus").textContent =
          playing ? "Playing" : "Stopped";
      }
    } catch (error) {
      console.warn(
        "Media status unavailable:",
        error.message
      );

      if ($("mlTotalCount")) {
        $("mlTotalCount").textContent =
          mediaItems.length;
      }
    }
  }

  async function loadCategories() {
    try {
      const data = await request(
        "/media/categories"
      );

      categories =
        normalizeCategories(data)
          .map(category => {
            if (typeof category === "string") {
              return category;
            }

            return (
              category.name ||
              category.category ||
              ""
            );
          })
          .filter(Boolean);
    } catch (error) {
      console.warn(
        "Media categories unavailable:",
        error.message
      );
    }
  }

  async function loadMedia() {
    const body = $("mlTableBody");

    if (body) {
      body.innerHTML = `
        <tr>
          <td colspan="4" class="ml-empty">
            Loading media library…
          </td>
        </tr>
      `;
    }

    try {
      const data = await request("/media");

      mediaItems = normalizeItems(data);

      await loadCategories();

      renderCategoryOptions();
      renderItems();
      await loadStatus();

      setMessage(
        `Media library loaded: ${mediaItems.length} file(s).`,
        "success"
      );
    } catch (error) {
      mediaItems = [];
      renderCategoryOptions();
      renderItems();

      setMessage(
        `Media API error: ${error.message}`,
        "error"
      );
    }
  }

  async function uploadMedia(event) {
    event.preventDefault();

    const fileInput = $("mlFile");
    const nameInput = $("mlDisplayName");
    const categoryInput = $("mlUploadCategory");
    const button = $("mlUploadButton");
    const progress = $("mlProgress");

    const file = fileInput?.files?.[0];

    if (!file) {
      setMessage(
        "Please select an audio file.",
        "error"
      );
      return;
    }

    const displayName =
      nameInput?.value.trim() ||
      file.name.replace(/\.[^.]+$/, "");

    const category =
      categoryInput?.value || "Custom";

    const formData = new FormData();

    formData.append("file", file);
    formData.append("display_name", displayName);
    formData.append("name", displayName);
    formData.append("category", category);

    try {
      button.disabled = true;
      progress.classList.add("visible");

      setMessage("");

      await request(
        "/media/upload",
        {
          method: "POST",
          body: formData
        }
      );

      fileInput.value = "";
      nameInput.value = "";

      setMessage(
        "Audio uploaded successfully.",
        "success"
      );

      await loadMedia();
    } catch (error) {
      setMessage(
        `Upload failed: ${error.message}`,
        "error"
      );
    } finally {
      button.disabled = false;
      progress.classList.remove("visible");
    }
  }

  async function playMedia(id) {
    if (!id) {
      setMessage(
        "Media ID is missing.",
        "error"
      );
      return;
    }

    try {
      setMessage("Starting playback…");

      await request(
        `/media/${encodeURIComponent(id)}/play`,
        {
          method: "POST"
        }
      );

      if ($("mlPlaybackStatus")) {
        $("mlPlaybackStatus").textContent =
          "Playing";
      }

      setMessage(
        "Audio playback started.",
        "success"
      );
    } catch (error) {
      setMessage(
        `Playback failed: ${error.message}`,
        "error"
      );
    }
  }

  async function stopMedia() {
    try {
      await request(
        "/media/stop",
        {
          method: "POST"
        }
      );

      if ($("mlPlaybackStatus")) {
        $("mlPlaybackStatus").textContent =
          "Stopped";
      }

      setMessage(
        "Audio playback stopped.",
        "success"
      );
    } catch (error) {
      setMessage(
        `Stop failed: ${error.message}`,
        "error"
      );
    }
  }

  async function deleteMedia(id, name) {
    if (!id) {
      setMessage(
        "Media ID is missing.",
        "error"
      );
      return;
    }

    const confirmed = window.confirm(
      `Delete "${name || "this audio"}"?`
    );

    if (!confirmed) {
      return;
    }

    try {
      await request(
        `/media/${encodeURIComponent(id)}`,
        {
          method: "DELETE"
        }
      );

      setMessage(
        "Audio deleted successfully.",
        "success"
      );

      await loadMedia();
    } catch (error) {
      setMessage(
        `Delete failed: ${error.message}`,
        "error"
      );
    }
  }

  function bindEvents() {
    if (initialized) {
      return;
    }

    initialized = true;

    $("mlUploadForm")?.addEventListener(
      "submit",
      uploadMedia
    );

    $("mlRefresh")?.addEventListener(
      "click",
      loadMedia
    );

    $("mlSearch")?.addEventListener(
      "input",
      renderItems
    );

    $("mlCategoryFilter")?.addEventListener(
      "change",
      renderItems
    );

    $("mlFile")?.addEventListener(
      "change",
      event => {
        const file = event.target.files?.[0];
        const nameInput = $("mlDisplayName");

        if (
          file &&
          nameInput &&
          !nameInput.value.trim()
        ) {
          nameInput.value =
            file.name.replace(/\.[^.]+$/, "");
        }
      }
    );

    $("mlTableBody")?.addEventListener(
      "click",
      event => {
        const button = event.target.closest(
          "[data-ml-action]"
        );

        if (!button) {
          return;
        }

        const action = button.dataset.mlAction;
        const id = button.dataset.mediaId;
        const name = button.dataset.mediaName;

        if (action === "play") {
          playMedia(id);
        }

        if (action === "stop") {
          stopMedia();
        }

        if (action === "delete") {
          deleteMedia(id, name);
        }
      }
    );
  }

  function registerPage() {
    const router = window.NoorRouter;

    if (
      router &&
      typeof router.register === "function" &&
      !router.exists("media-library")
    ) {
      router.register(
        "media-library",
        {
          title: "Media Library",
          subtitle:
            "Upload and manage NoorBrain audio",
          onOpen: loadMedia
        }
      );
    }
  }

  function initialize() {
    buildPage();
    bindEvents();
    registerPage();
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initialize
    );
  } else {
    initialize();
  }

  window.NoorMediaLibrary = {
    refresh: loadMedia,
    play: playMedia,
    stop: stopMedia
  };
})();
