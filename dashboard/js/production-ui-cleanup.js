(() => {
  "use strict";

  if (window.NoorBrainProductionCleanup?.installed) return;

  const hiddenClass = "nb-production-hidden";
  let running = false;

  function text(element) {
    return String(element?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function cardFor(element) {
    return element?.closest?.(
      "section, article, .mobile-card, .card, [class*='camera-card'], " +
      "[class*='camera-panel'], [class*='product-card'], [class*='panel']"
    ) || null;
  }

  function hide(element, reason) {
    if (!element || element.dataset.nbProductionHidden === "1") return false;
    element.dataset.nbProductionHidden = "1";
    element.dataset.nbProductionReason = reason;
    element.classList.add(hiddenClass);
    element.setAttribute("aria-hidden", "true");
    return true;
  }

  function hideBrokenDuplicateCamera() {
    const workingCameraExists = [...document.querySelectorAll("section, article, div")]
      .some(element => {
        const value = text(element);
        return (
          value.includes("Camera & Vision Product") ||
          (value.includes("Primary Camera") && value.includes("Reconnect"))
        );
      });

    if (!workingCameraExists) return 0;

    let hidden = 0;
    const candidates = [...document.querySelectorAll("section, article, div")]
      .filter(element => {
        const value = text(element);
        return (
          value.includes("Hall Camera unavailable") &&
          value.includes("Camera 2") &&
          value.includes("Camera 6") &&
          !value.includes("Camera & Vision Product") &&
          !value.includes("Primary Camera")
        );
      })
      .sort((left, right) => text(left).length - text(right).length);

    const duplicate = candidates[0];
    if (duplicate) {
      const card = cardFor(duplicate) || duplicate;
      if (hide(card, "stale-duplicate-camera")) hidden += 1;
    }
    return hidden;
  }

  function hideSprintLabels() {
    let hidden = 0;
    const pattern = /^SPRINT\s+(?:\d+|[A-Z]\d+)(?:[A-Z0-9. -]*)?$/i;
    for (const element of document.querySelectorAll("small, span, label, p, div")) {
      if (element.children.length > 1) continue;
      const value = text(element);
      if (value.length <= 38 && pattern.test(value)) {
        if (hide(element, "developer-sprint-label")) hidden += 1;
      }
    }
    return hidden;
  }

  function hideSmokeActivityCards() {
    let hidden = 0;
    for (const element of document.querySelectorAll("article, li, [class*='activity'] > div")) {
      const value = text(element);
      if (/^Smoke Activity\b/i.test(value) || value.includes("Smoke Activity hall")) {
        if (hide(element, "smoke-test-activity")) hidden += 1;
      }
    }

    for (const element of document.querySelectorAll("strong, b, h3, h4")) {
      if (text(element) !== "Smoke Activity") continue;
      const card = element.closest("article, li, [class*='activity-card'], [class*='timeline'] > div");
      if (hide(card, "smoke-test-activity")) hidden += 1;
    }
    return hidden;
  }

  function renameDeveloperTitles() {
    const replacements = new Map([
      ["Camera & Vision Product", "Camera & Vision"],
      ["Routine Intelligence Product", "Routine Intelligence"],
      ["Mobile AI Control Center", "AI Control Center"],
    ]);
    let renamed = 0;
    for (const element of document.querySelectorAll("h1, h2, h3, h4")) {
      const replacement = replacements.get(text(element));
      if (replacement) {
        element.textContent = replacement;
        renamed += 1;
      }
    }
    return renamed;
  }

  function removeEmptyRecentActivity() {
    for (const heading of document.querySelectorAll("h1, h2, h3, h4")) {
      if (text(heading) !== "Recent Activity") continue;
      const card = cardFor(heading);
      if (!card) continue;
      const visibleItems = [...card.querySelectorAll("article, li, [class*='activity'] > div")]
        .filter(item => !item.classList.contains(hiddenClass));
      if (visibleItems.length === 0) hide(card, "empty-test-activity-section");
    }
  }

  function clean() {
    if (running) return;
    running = true;
    try {
      const result = {
        cameras: hideBrokenDuplicateCamera(),
        sprintLabels: hideSprintLabels(),
        smokeActivities: hideSmokeActivityCards(),
        renamed: renameDeveloperTitles(),
      };
      removeEmptyRecentActivity();
      window.dispatchEvent(new CustomEvent("noorbrain:production-ui-cleaned", {
        detail: result,
      }));
    } finally {
      running = false;
    }
  }

  let timer = 0;
  const observer = new MutationObserver(() => {
    clearTimeout(timer);
    timer = window.setTimeout(clean, 80);
  });

  function start() {
    clean();
    observer.observe(document.body, {childList: true, subtree: true});
    window.setTimeout(clean, 500);
    window.setTimeout(clean, 1800);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }

  window.NoorBrainProductionCleanup = Object.freeze({
    installed: true,
    version: "1.0.0",
    clean,
  });
})();
