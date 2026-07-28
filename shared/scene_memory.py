"""
============================================================
Project : NoorBrain
Module  : Scene Memory
Version : 2.0.0
============================================================
"""

import time

from shared.logger import logger


class SceneMemory:

    def __init__(self):

        self.people = {}

    # ----------------------------------------------------

    def update(self, detections):

        now = time.time()

        active = set()

        for detection in detections:

            if detection.get("label") != "person":
                continue

            person_id = "person"

            zone = detection.get("zone", "Unknown")
            confidence = detection.get("confidence", 0)

            active.add(person_id)

            if person_id not in self.people:

                self.people[person_id] = {
                    "first_seen": now,
                    "last_seen": now,
                    "zone": zone,
                    "previous_zone": zone,
                    "confidence": confidence
                }

                logger.info(f"Person entered {zone}")

            else:

                person = self.people[person_id]

                if person["zone"] != zone:

                    logger.info(
                        f"Person moved {person['zone']} -> {zone}"
                    )

                    person["previous_zone"] = person["zone"]
                    person["zone"] = zone

                person["last_seen"] = now
                person["confidence"] = confidence

        timeout = 5

        remove = []

        for person_id, info in self.people.items():

            if person_id not in active:

                if now - info["last_seen"] > timeout:

                    duration = round(
                        info["last_seen"] - info["first_seen"],
                        1
                    )

                    logger.info(
                        f"Person left after {duration}s"
                    )

                    remove.append(person_id)

        for person_id in remove:
            del self.people[person_id]

    # ----------------------------------------------------

    def snapshot(self):

        result = []

        now = time.time()

        for person in self.people.values():

            result.append({

                "zone": person["zone"],
                "previous_zone": person["previous_zone"],
                "seconds_visible": round(
                    now - person["first_seen"],
                    1
                ),
                "confidence": person["confidence"]

            })

        return result

    # ----------------------------------------------------

    def person_count(self):

        return len(self.people)


scene_memory = SceneMemory()
