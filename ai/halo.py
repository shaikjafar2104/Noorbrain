"""
============================================================
Project : NoorBrain
Module  : HALO AI
Version : 1.0.0
============================================================
"""

import threading
import time

from shared.logger import logger
from ai.ollama_client import ollama_client
from ai.prompt_builder import prompt_builder
from ai.memory import memory


class HALO:

    def __init__(self):

        self._lock = threading.Lock()

        self.running = False

        self.last_message = None

        self.last_response = None

        self.created = time.time()

        logger.info("HALO Initialized")

    # ----------------------------------------------------

    def ask(self, message):

        with self._lock:

            self.last_message = message

            memory.add(
                "User",
                message
            )

            prompt = self._think(message)

            response = ollama_client.generate(prompt)

            memory.add(
                "HALO",
                response
            )

            self.last_response = response

            return response

    # ----------------------------------------------------

    def _think(self, message):

        prompt = prompt_builder.build(message)

        history = memory.build()

        if history:

            prompt += "\n\nConversation History:\n"

            prompt += history

        return prompt

    # ----------------------------------------------------

    def snapshot(self):

        return {

            "running": self.running,

            "created": self.created,

            "last_message": self.last_message,

            "last_response": self.last_response,

            "history_count": len(memory.history)

        }


# ----------------------------------------------------

halo = HALO()


# ----------------------------------------------------

if __name__ == "__main__":

    print("=" * 60)
    print("HALO Interactive Console")
    print("Type 'exit' to quit")
    print("=" * 60)

    while True:

        try:

            question = input("\nYou : ")

            if question.lower() in ("exit", "quit"):

                break

            answer = halo.ask(question)

            print(f"\nHALO : {answer}")

        except KeyboardInterrupt:

            break

        except Exception as ex:

            logger.exception(ex)

            print(f"\nError : {ex}")
