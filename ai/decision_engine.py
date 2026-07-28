"""
============================================================
Project : NoorBrain
Module  : Decision Engine
Version : 1.0.0
============================================================
"""

import threading
import time

from shared.logger import logger


class DecisionEngine:

    def __init__(self):

        self._lock = threading.Lock()

        self.last_event = None

        self.last_time = 0

        self.cooldown = 2

    # ----------------------------------------------------

    def process(self, detections):

        if not detections:

            return None

        detection = detections[0]

        zone = detection.get(

            "zone",

            "Unknown"

        )

        label = detection.get(

            "label",

            "object"

        )

        confidence = detection.get(

            "confidence",

            0

        )

        now = time.time()

        with self._lock:

            if (

                self.last_event == zone

                and

                now - self.last_time

                < self.cooldown

            ):

                return None

            self.last_event = zone

            self.last_time = now

            decision = {

                "action": "notify",

                "label": label,

                "zone": zone,

                "confidence": confidence,

                "timestamp": now

            }

            logger.info(

                f"Decision : {decision}"

            )

            return decision
    # ----------------------------------------------------

    def should_notify(

        self,

        decision

    ):

        if decision is None:

            return False

        return (

            decision["action"]

            ==

            "notify"

        )

    # ----------------------------------------------------

    def should_ignore(

        self,

        decision

    ):

        return decision is None

    # ----------------------------------------------------

    def summary(

        self,

        decision

    ):

        if decision is None:

            return "No Decision"

        return (

            f'{decision["label"]} '

            f'in '

            f'{decision["zone"]} '

            f'({decision["confidence"]:.2f})'

        )

    # ----------------------------------------------------

    def snapshot(self):

        return {

            "last_event": self.last_event,

            "last_time": self.last_time,

            "cooldown": self.cooldown

        }


decision_engine = DecisionEngine()

