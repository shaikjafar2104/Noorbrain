"""
============================================================
Project : NoorBrain
Module  : HALO Memory
Version : 1.0.0
============================================================
"""

from collections import deque


class Memory:

    def __init__(self):

        self.history = deque(maxlen=20)

    def add(self, role, message):

        self.history.append({

            "role": role,

            "message": message

        })

    def build(self):

        lines = []

        for item in self.history:

            lines.append(

                f"{item['role']}: {item['message']}"

            )

        return "\n".join(lines)

    def clear(self):

        self.history.clear()


memory = Memory()
