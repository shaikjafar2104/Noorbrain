(() => {
    "use strict";

    function findHaloInput() {
        return (
            document.querySelector('input[placeholder*="Ask HALO" i]') ||
            document.querySelector('textarea[placeholder*="Ask HALO" i]') ||
            document.querySelector("#halo-input") ||
            document.querySelector(".halo-input")
        );
    }

    function findSendButton(input) {
        if (!input) return null;

        const parent = input.parentElement;

        if (parent) {
            const localButtons = [...parent.querySelectorAll("button")];
            const localSend = localButtons.find(button =>
                button.textContent.trim().toLowerCase() === "send"
            );

            if (localSend) return localSend;
        }

        return [...document.querySelectorAll("button")].find(button =>
            button.textContent.trim().toLowerCase() === "send"
        ) || null;
    }

    function findMessageArea(input) {
        if (!input) return null;

        let current = input.parentElement;

        while (current && current !== document.body) {
            const candidates = [...current.querySelectorAll("div")].filter(element => {
                const style = window.getComputedStyle(element);
                const height = element.getBoundingClientRect().height;

                return (
                    height > 180 &&
                    (
                        style.overflowY === "auto" ||
                        style.overflowY === "scroll"
                    )
                );
            });

            if (candidates.length) {
                return candidates.sort(
                    (a, b) =>
                        b.getBoundingClientRect().height -
                        a.getBoundingClientRect().height
                )[0];
            }

            current = current.parentElement;
        }

        const greeting = [...document.querySelectorAll("div, p, span")].find(
            element =>
                element.textContent.includes(
                    "Assalamu Alaikum. I am HALO"
                )
        );

        return greeting?.parentElement?.parentElement || null;
    }

    function createMessage(role, text) {
        const wrapper = document.createElement("div");

        wrapper.style.display = "flex";
        wrapper.style.margin = "10px 14px";
        wrapper.style.justifyContent =
            role === "user" ? "flex-end" : "flex-start";

        const bubble = document.createElement("div");

        bubble.textContent = text;
        bubble.style.maxWidth = "78%";
        bubble.style.padding = "10px 14px";
        bubble.style.borderRadius = "12px";
        bubble.style.whiteSpace = "pre-wrap";
        bubble.style.wordBreak = "break-word";
        bubble.style.lineHeight = "1.45";

        if (role === "user") {
            bubble.style.background = "#10b981";
            bubble.style.color = "#061611";
            bubble.style.borderBottomRightRadius = "4px";
        } else {
            bubble.style.background = "#1e293b";
            bubble.style.color = "#f8fafc";
            bubble.style.borderBottomLeftRadius = "4px";
        }

        wrapper.appendChild(bubble);
        return wrapper;
    }

    function appendMessage(area, role, text) {
        if (!area) {
            console.error("HALO message area not found.");
            return;
        }

        area.appendChild(createMessage(role, text));
        area.scrollTop = area.scrollHeight;
    }

    async function sendHaloMessage() {
        const input = findHaloInput();
        const area = findMessageArea(input);

        if (!input) {
            console.error("HALO input not found.");
            return;
        }

        const message = String(input.value || "").trim();

        if (!message) return;

        input.value = "";
        input.disabled = true;

        const button = findSendButton(input);

        if (button) {
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.textContent = "Thinking...";
        }

        appendMessage(area, "user", message);

        const waitingMessage = createMessage(
            "assistant",
            "HALO is thinking..."
        );

        area?.appendChild(waitingMessage);
        if (area) area.scrollTop = area.scrollHeight;

        const controller = new AbortController();
        const timeoutId = setTimeout(
            () => controller.abort(),
            120000
        );

        try {
            const response = await fetch("/api/halo/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({message}),
                signal: controller.signal
            });

            const rawBody = await response.text();

            let payload;

            try {
                payload = JSON.parse(rawBody);
            } catch {
                payload = {
                    response: rawBody
                };
            }

            if (!response.ok) {
                throw new Error(
                    payload.detail ||
                    payload.error ||
                    `HTTP ${response.status}`
                );
            }

            const reply =
                payload.response ??
                payload.reply ??
                payload.answer ??
                payload.message ??
                payload.content ??
                payload.result?.response ??
                payload.result?.reply;

            waitingMessage.remove();

            appendMessage(
                area,
                "assistant",
                String(reply || "HALO returned an empty response.")
            );
        } catch (error) {
            waitingMessage.remove();

            let errorText;

            if (error?.name === "AbortError") {
                errorText = "HALO response timed out.";
            } else {
                errorText = `HALO error: ${error?.message || error}`;
            }

            appendMessage(area, "assistant", errorText);
            console.error("HALO request failed:", error);
        } finally {
            clearTimeout(timeoutId);
            input.disabled = false;
            input.focus();

            if (button) {
                button.disabled = false;
                button.textContent =
                    button.dataset.originalText || "Send";
            }
        }
    }

    function bindHalo() {
        const input = findHaloInput();
        const button = findSendButton(input);

        if (!input || !button) {
            console.warn(
                "HALO controls not found yet; retrying..."
            );

            setTimeout(bindHalo, 1000);
            return;
        }

        if (button.dataset.noorHaloBound === "true") {
            return;
        }

        button.dataset.noorHaloBound = "true";

        button.addEventListener(
            "click",
            event => {
                event.preventDefault();
                event.stopImmediatePropagation();
                sendHaloMessage();
            },
            true
        );

        input.addEventListener(
            "keydown",
            event => {
                if (
                    event.key === "Enter" &&
                    !event.shiftKey
                ) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    sendHaloMessage();
                }
            },
            true
        );

        console.log(
            "NoorBrain HALO Studio handler successfully attached."
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            bindHalo
        );
    } else {
        bindHalo();
    }

    window.NoorHALO = {
        send: sendHaloMessage,
        bind: bindHalo
    };
})();
