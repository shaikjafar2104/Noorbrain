(() => {
    "use strict";

    const inputSelectors = [
        "#halo-input",
        "#ai-input",
        "#chat-input",
        "#message-input",
        'textarea[name="message"]',
        'input[name="message"]',
        ".halo-input",
        ".chat-input"
    ];

    const outputSelectors = [
        "#halo-messages",
        "#ai-messages",
        "#chat-messages",
        "#messages",
        ".halo-messages",
        ".chat-messages",
        ".messages"
    ];

    const buttonSelectors = [
        "#halo-send",
        "#ai-send",
        "#chat-send",
        "#send-message",
        'button[data-action="halo-send"]',
        'button[type="submit"]'
    ];

    function firstMatch(selectors) {
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                return element;
            }
        }
        return null;
    }

    function appendMessage(role, text) {
        const output = firstMatch(outputSelectors);

        if (!output) {
            console.warn(
                "HALO: message container not found.",
                text
            );
            return;
        }

        const message = document.createElement("div");
        message.className =
            role === "user"
                ? "halo-message halo-user-message"
                : "halo-message halo-ai-message";

        const label = document.createElement("strong");
        label.textContent =
            role === "user" ? "You: " : "HALO: ";

        const content = document.createElement("span");
        content.textContent = text;

        message.append(label, content);
        output.appendChild(message);
        output.scrollTop = output.scrollHeight;
    }

    async function sendToHalo(rawMessage) {
        const message = String(rawMessage || "").trim();

        if (!message) {
            return;
        }

        appendMessage("user", message);

        const controller = new AbortController();
        const timeoutId = setTimeout(
            () => controller.abort(),
            120000
        );

        try {
            const response = await fetch("/api/halo/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({message}),
                signal: controller.signal
            });

            const raw = await response.text();

            let data;
            try {
                data = JSON.parse(raw);
            } catch {
                data = {response: raw};
            }

            if (!response.ok) {
                const detail =
                    data.detail ??
                    data.error ??
                    `HTTP ${response.status}`;

                throw new Error(String(detail));
            }

            const reply =
                data.response ??
                data.reply ??
                data.answer ??
                data.message ??
                data.content ??
                data.result?.response ??
                data.result?.reply;

            appendMessage(
                "assistant",
                reply || "HALO returned an empty response."
            );
        } catch (error) {
            const message =
                error?.name === "AbortError"
                    ? "HALO response timed out."
                    : `HALO error: ${error?.message || error}`;

            appendMessage("assistant", message);
            console.error(error);
        } finally {
            clearTimeout(timeoutId);
        }
    }

    function bindHalo() {
        const input = firstMatch(inputSelectors);
        const button = firstMatch(buttonSelectors);

        if (!input || !button) {
            console.warn(
                "HALO: input or send button not found.",
                {input, button}
            );
            return;
        }

        if (button.dataset.haloBound === "true") {
            return;
        }

        button.dataset.haloBound = "true";

        const submit = async event => {
            event.preventDefault();
            event.stopImmediatePropagation();

            const message = input.value;
            input.value = "";
            await sendToHalo(message);
        };

        button.addEventListener("click", submit, true);

        const form = input.closest("form");
        if (form) {
            form.addEventListener("submit", submit, true);
        }

        input.addEventListener("keydown", event => {
            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {
                event.preventDefault();
                button.click();
            }
        });

        console.info("HALO dashboard handler active.");
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            bindHalo
        );
    } else {
        bindHalo();
    }

    window.NoorBrainHALO = {
        send: sendToHalo,
        bind: bindHalo
    };
})();
