(() => {
  "use strict";
  if (window.NoorBrainReleaseV14?.installed) return;
  const API = "/api/platform-release-v14";

  async function api(path) {
    const response = await fetch(API + path, {cache: "no-store"});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  }

  function panel() {
    let root = document.getElementById("nbReleaseV14");
    if (root) return root;
    const host = document.querySelector("main") || document.querySelector(".mobile-main") || document.body;
    root = document.createElement("section");
    root.id = "nbReleaseV14";
    root.className = "nb-release-v14";
    root.innerHTML = `
      <div class="nb-r14-head">
        <div class="nb-r14-mark">N</div>
        <div><small>NOORBRAIN PLATFORM</small><h2>Production Release</h2><p id="nbR14Status">Running system audit…</p></div>
        <button id="nbR14Refresh" type="button">Audit</button>
      </div>
      <div class="nb-r14-progress"><i id="nbR14Bar"></i></div>
      <div id="nbR14Components" class="nb-r14-components"></div>
      <div class="nb-r14-foot"><span id="nbR14Ready">Checking…</span><span>v14.0.0</span></div>
    `;
    host.appendChild(root);
    root.querySelector("#nbR14Refresh").onclick = load;
    return root;
  }

  async function load() {
    const root = panel();
    const status = root.querySelector("#nbR14Status");
    try {
      const result = await api("/audit");
      const percent = Math.round(result.ready / result.total * 100);
      root.querySelector("#nbR14Bar").style.width = `${percent}%`;
      root.querySelector("#nbR14Components").innerHTML = Object.entries(result.components)
        .map(([name, item]) => `<span class="${item.ready ? "ready" : "missing"}">${item.ready ? "✓" : "!"} ${name.replaceAll("_", " ")}</span>`)
        .join("");
      root.querySelector("#nbR14Ready").textContent = `${result.ready}/${result.total} components ready`;
      status.textContent = result.status === "production" ? "NoorBrain production system ready" : "Some components need attention";
      root.classList.toggle("is-production", result.status === "production");
    } catch (error) {
      status.textContent = `Audit unavailable: ${error.message}`;
    }
  }

  function start() { panel(); load(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
  window.NoorBrainReleaseV14 = Object.freeze({installed: true, version: "14.0.0", load});
})();
