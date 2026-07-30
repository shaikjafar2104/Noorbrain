(() => {
  "use strict";

  const API = "/api/ui-recovery";
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(API + path, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    const contentType =
      response.headers.get("content-type") || "";

    const body = contentType.includes("application/json")
      ? await response.json()
      : {detail: await response.text()};

    if (!response.ok) {
      throw new Error(
        body.detail || `HTTP ${response.status}`
      );
    }

    return body;
  }

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function hideLegacyAutomation() {
    [
      "smartAutomationPanel",
      "automationExecutionPanel"
    ].forEach(id => {
      const element = $(id);

      if (element) {
        element.classList.add(
          "nb-ui-recovery-hidden"
        );
      }
    });
  }

  function automationHost() {
    return (
      $("smartAutomationPanel")?.parentElement
      || $("page-insights")
      || $("page-dashboard")
      || document.querySelector("main.main")
      || document.querySelector("main")
    );
  }

  function ensureAutomationPanel() {
    hideLegacyAutomation();

    const host = automationHost();

    if (!host) return false;

    if (!$("nbFriendlyAutomation")) {
      const panel = document.createElement("section");
      panel.id = "nbFriendlyAutomation";
      panel.className =
        "card nb-ui-recovery-card";

      panel.innerHTML = `
        <div class="card-head nb-recovery-head">
          <div>
            <h2>Smart Automation</h2>
            <p>Create simple rules without editing JSON.</p>
          </div>
          <button
            id="nbAutomationRefresh"
            class="button secondary"
          >
            Refresh
          </button>
        </div>

        <div class="nb-automation-layout">
          <form
            id="nbAutomationForm"
            class="nb-automation-form"
          >
            <label>
              Rule name
              <input
                id="nbRuleName"
                value="Hall Welcome"
                placeholder="Example: Hall Welcome"
              >
            </label>

            <label>
              Zone
              <input
                id="nbRuleZone"
                value="Hall"
                placeholder="Hall"
              >
            </label>

            <label>
              When
              <select id="nbRuleCondition">
                <option value="person_present">
                  Person is present
                </option>
                <option value="person_entered">
                  Person enters
                </option>
                <option value="person_exited">
                  Person exits
                </option>
              </select>
            </label>

            <label>
              Action
              <select id="nbRuleAction">
                <option value="halo_speak">
                  HALO speaks
                </option>
                <option value="remember">
                  Save to HALO memory
                </option>
                <option value="halo_respond">
                  HALO responds
                </option>
              </select>
            </label>

            <label class="nb-form-wide">
              Message
              <textarea
                id="nbRuleMessage"
                rows="3"
              >Someone is in the Hall.</textarea>
            </label>

            <div class="nb-form-wide">
              <button
                type="submit"
                class="button success"
              >
                Save Automation
              </button>
            </div>
          </form>

          <div>
            <div
              id="nbAutomationSummary"
              class="nb-status-strip"
            >
              Loading…
            </div>

            <div
              id="nbAutomationRules"
              class="nb-automation-rules"
            >
              No rules.
            </div>
          </div>
        </div>
      `;

      if ($("smartAutomationPanel")) {
        $("smartAutomationPanel")
          .insertAdjacentElement(
            "afterend",
            panel
          );
      } else {
        host.appendChild(panel);
      }

      $("nbAutomationRefresh")
        ?.addEventListener(
          "click",
          loadAutomation,
        );

      $("nbAutomationForm")
        ?.addEventListener(
          "submit",
          createRule,
        );
    }

    return true;
  }

  async function createRule(event) {
    event.preventDefault();

    const message = $("nbRuleMessage");

    try {
      await api(
        "/automation/rules",
        {
          method: "POST",
          body: JSON.stringify({
            name:
              $("nbRuleName")
                ?.value
                ?.trim(),
            zone:
              $("nbRuleZone")
                ?.value
                ?.trim(),
            condition:
              $("nbRuleCondition")
                ?.value,
            action:
              $("nbRuleAction")
                ?.value,
            message:
              message
                ?.value
                ?.trim(),
          })
        }
      );

      showToast(
        "Automation rule created.",
        "success"
      );
      await loadAutomation();
    } catch (error) {
      showToast(
        `Create failed: ${error.message}`,
        "error"
      );
    }
  }

  async function toggleRule(ruleId) {
    try {
      await api(
        `/automation/rules/${encodeURIComponent(
          ruleId
        )}/toggle`,
        {method: "POST"}
      );
      await loadAutomation();
    } catch (error) {
      showToast(
        `Toggle failed: ${error.message}`,
        "error"
      );
    }
  }

  async function runRule(ruleId, zone) {
    try {
      const result = await api(
        `/automation/rules/${encodeURIComponent(
          ruleId
        )}/run`,
        {
          method: "POST",
          body: JSON.stringify({zone})
        }
      );

      showToast(
        result.status === "completed"
          ? "Automation completed."
          : `Automation: ${result.status}`,
        result.status === "completed"
          ? "success"
          : "info"
      );

      await loadAutomation();
    } catch (error) {
      showToast(
        `Run failed: ${error.message}`,
        "error"
      );
    }
  }

  async function deleteRule(ruleId) {
    if (!confirm("Delete this automation rule?")) {
      return;
    }

    try {
      await api(
        `/automation/rules/${encodeURIComponent(
          ruleId
        )}`,
        {method: "DELETE"}
      );

      await loadAutomation();
    } catch (error) {
      showToast(
        `Delete failed: ${error.message}`,
        "error"
      );
    }
  }

  async function loadAutomation() {
    const summary = $("nbAutomationSummary");
    const list = $("nbAutomationRules");

    if (!summary || !list) return;

    summary.textContent = "Refreshing…";

    try {
      const result = await api(
        "/automation/overview"
      );

      summary.textContent =
        `${result.enabled_count}/${result.rule_count} enabled`
        + ` · ${result.runs.length} recent runs`;

      list.innerHTML = result.rules?.length
        ? result.rules.map(rule => {
            const zone =
              rule.conditions?.find(
                item => item.kind === "zone"
              )?.value || "Any zone";

            const action =
              rule.actions?.[0]?.name
              || "Action";

            return `
              <article class="nb-rule-card">
                <div>
                  <div class="nb-rule-title-row">
                    <strong>${safe(rule.name)}</strong>
                    <span
                      class="nb-state-pill ${
                        rule.enabled
                          ? "is-enabled"
                          : "is-disabled"
                      }"
                    >
                      ${
                        rule.enabled
                          ? "Enabled"
                          : "Disabled"
                      }
                    </span>
                  </div>

                  <div class="nb-rule-meta">
                    ${safe(zone)}
                    · ${safe(action)}
                    · ${safe(
                      rule.run_count || 0
                    )} runs
                  </div>
                </div>

                <div class="nb-rule-actions">
                  <button
                    class="button secondary"
                    data-nb-action="run"
                    data-rule="${safe(rule.id)}"
                    data-zone="${safe(zone)}"
                  >
                    Run now
                  </button>

                  <button
                    class="button secondary"
                    data-nb-action="toggle"
                    data-rule="${safe(rule.id)}"
                  >
                    ${
                      rule.enabled
                        ? "Disable"
                        : "Enable"
                    }
                  </button>

                  <button
                    class="button danger"
                    data-nb-action="delete"
                    data-rule="${safe(rule.id)}"
                  >
                    Delete
                  </button>
                </div>
              </article>
            `;
          }).join("")
        : `
            <div class="nb-empty-state">
              No automation rules yet.
            </div>
          `;

      list
        .querySelectorAll("[data-nb-action]")
        .forEach(button => {
          button.addEventListener(
            "click",
            () => {
              const action =
                button.dataset.nbAction;
              const ruleId =
                button.dataset.rule;

              if (action === "run") {
                runRule(
                  ruleId,
                  button.dataset.zone
                );
              } else if (
                action === "toggle"
              ) {
                toggleRule(ruleId);
              } else if (
                action === "delete"
              ) {
                deleteRule(ruleId);
              }
            }
          );
        });
    } catch (error) {
      summary.textContent =
        `Automation unavailable: ${error.message}`;
      list.innerHTML = `
        <div class="nb-error-state">
          Check backend and press Refresh.
        </div>
      `;
    }
  }

  function repairGlobalRefresh() {
    const button = $("refreshBtn");

    if (
      !button
      || button.dataset
        .nbRecoveryBound === "true"
    ) {
      return;
    }

    button.dataset.nbRecoveryBound = "true";

    button.addEventListener(
      "click",
      async () => {
        button.disabled = true;
        const original =
          button.textContent;
        button.textContent =
          "Refreshing…";

        try {
          window.dispatchEvent(
            new CustomEvent(
              "noorbrain:refresh"
            )
          );

          await Promise.allSettled([
            loadAutomation(),
            window
              .NoorBrainHabitLearning
              ?.refresh?.(),
            window
              .NoorBrainPrayerIntelligence
              ?.refresh?.(),
            window
              .NoorBrainIslamicReminders
              ?.refresh?.(),
            window
              .NoorBrainNotificationFinal
              ?.refresh?.(),
          ]);

          document
            .querySelectorAll(
              "img[data-stream]"
            )
            .forEach(image => {
              const source =
                image.src.split("&_refresh=")[0]
                  .split("?_refresh=")[0];
              const separator =
                source.includes("?")
                  ? "&"
                  : "?";

              image.src =
                `${source}${separator}`
                + `_refresh=${Date.now()}`;
            });

          showToast(
            "Dashboard refreshed.",
            "success"
          );
        } finally {
          button.disabled = false;
          button.textContent =
            original;
        }
      },
      true,
    );
  }

  function showToast(message, kind = "info") {
    let toast = $("nbRecoveryToast");

    if (!toast) {
      toast = document.createElement("div");
      toast.id = "nbRecoveryToast";
      document.body.appendChild(toast);
    }

    toast.className =
      `nb-recovery-toast ${kind}`;
    toast.textContent = message;

    clearTimeout(
      window.nbRecoveryToastTimer
    );

    window.nbRecoveryToastTimer =
      setTimeout(() => {
        toast.classList.remove("show");
      }, 2800);

    requestAnimationFrame(() => {
      toast.classList.add("show");
    });
  }

  function mount() {
    const automationReady =
      ensureAutomationPanel();

    repairGlobalRefresh();

    if (automationReady) {
      loadAutomation();
    }

    return automationReady;
  }

  const observer =
    new MutationObserver(() => {
      if (ensureAutomationPanel()) {
        repairGlobalRefresh();
        observer.disconnect();
        loadAutomation();
      }
    });

  if (mount()) {
    observer.disconnect();
  } else {
    observer.observe(
      document.documentElement,
      {
        childList: true,
        subtree: true
      }
    );
  }

  window.NoorBrainUIRecovery = {
    mount,
    refresh: loadAutomation,
    toast: showToast
  };
})();
