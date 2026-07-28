from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .cache import agent_cache


class LocalDialogue:
    def __init__(self) -> None:
        self.url = os.getenv(
            "OLLAMA_GENERATE_URL",
            "http://127.0.0.1:11434/api/generate",
        )
        self.model = os.getenv("HALO_FAST_MODEL", os.getenv("OLLAMA_MODEL", "llama3:latest"))

    @staticmethod
    def _instant_reply(text: str) -> str | None:
        normalized = " ".join(text.casefold().split()).strip(" ?!.")

        replies = {
            "assalamu alaikum": "Wa Alaikum Assalam. How can I help?",
            "salam": "Wa Alaikum Assalam. How can I help?",
            "hello": "Hello. How can I help?",
            "hi": "Hello. How can I help?",
            "thank you": "You are welcome.",
            "thanks": "You are welcome.",
            "who are you": "I am HALO, your local NoorBrain assistant.",
        }
        return replies.get(normalized)

    def chat(self, text: str) -> str:
        instant = self._instant_reply(text)
        if instant is not None:
            return instant

        cache_key = f"dialogue:{self.model}:{text.strip().casefold()}"
        return agent_cache.get_or_set(
            cache_key,
            300.0,
            lambda: self._generate(text),
        )

    def _generate(self, text: str) -> str:
        payload = {
            "model": self.model,
            "prompt": (
                "You are HALO, a fast offline NoorBrain assistant. "
                "Answer in one or two short sentences. Never invent device, "
                "automation, camera, or sensor facts. Smart-home facts must "
                "come from verified tools.\\n\\n"
                f"User: {text}\\nHALO:"
            ),
            "stream": False,
            "keep_alive": "24h",
            "options": {
                "num_predict": 64,
                "num_ctx": 1024,
                "temperature": 0.2,
                "top_p": 0.8,
            },
        }

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama unavailable: {exc.reason}") from exc

        reply = str(body.get("response") or "").strip()
        if not reply:
            raise RuntimeError("Ollama returned an empty response.")
        return reply


local_dialogue = LocalDialogue()
