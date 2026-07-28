"""
============================================================
Project : NoorBrain
Module  : Ollama Client
Version : 1.0.0
============================================================
"""

import requests

from shared.logger import logger
from shared.config_manager import load_config


class OllamaClient:

    def __init__(self):

        config = load_config()
        ai = config.get("ai", {})

        self.host = ai.get(
            "host",
            "http://127.0.0.1:11434"
        )

        self.model = ai.get(
            "model",
            "llama3:latest"
        )

        self.timeout = ai.get(
            "timeout",
            60
        )

        self.api = self.host + "/api/generate"

        logger.info(f"Ollama Model : {self.model}")

    # ----------------------------------------------------

    def generate(self, prompt):

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:

            print("\n" + "=" * 60)
            print("PROMPT SENT TO OLLAMA")
            print("=" * 60)
            print(prompt)
            print("=" * 60)

            response = requests.post(
                self.api,
                json=payload,
                timeout=self.timeout
            )

            print("Status :", response.status_code)
            print("Body :", response.text)

            response.raise_for_status()

            data = response.json()

            return data.get(
                "response",
                ""
            ).strip()

        except Exception as ex:

            print("\nOLLAMA ERROR")
            print(ex)

            logger.exception(ex)

            return "I'm unable to answer right now."

    # ----------------------------------------------------

    def health(self):

        try:

            response = requests.get(
                self.host + "/api/tags",
                timeout=3
            )

            return response.status_code == 200

        except Exception:

            return False

    # ----------------------------------------------------

    def models(self):

        try:

            response = requests.get(
                self.host + "/api/tags",
                timeout=5
            )

            response.raise_for_status()

            data = response.json()

            return data.get(
                "models",
                []
            )

        except Exception as ex:

            logger.exception(ex)

            return []

    # ----------------------------------------------------

    def snapshot(self):

        return {

            "host": self.host,
            "model": self.model,
            "online": self.health(),
            "models": len(self.models())

        }


# ============================================================

ollama_client = OllamaClient()
