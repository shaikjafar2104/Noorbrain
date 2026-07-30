(() => {
  "use strict";

  const $ = id => document.getElementById(id);

  function setText(id, value) {
    const element = $(id);

    if (element) {
      element.textContent = value;
    }
  }

  function bind(id, eventName, handler) {
    const element = $(id);

    if (element) {
      element.addEventListener(
        eventName,
        handler
      );
    }
  }

  function backendStatus(online) {
    const dot = $("backendDot");
    const text = $("backendText");

    if (dot) {
      dot.className =
        `dot ${online ? "online" : "offline"}`;
    }

    if (text) {
      text.textContent = online
        ? "Backend online"
        : "Backend offline";
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  window.NoorUI = {
    $,
    setText,
    bind,
    backendStatus,
    escapeHtml
  };
})();
