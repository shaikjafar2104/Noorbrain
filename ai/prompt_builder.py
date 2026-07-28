"""
============================================================
Project : NoorBrain
Module  : Prompt Builder
Version : 1.0.0
============================================================
"""
import time
from shared.logger import logger
from services.vision_engine import vision_engine
from services.camera_client import camera_client
from shared.detection_manager import detection_manager
from shared.scene_memory import scene_memory
from services.event_engine import event_engine
from shared.database import database
from shared.person_history import person_history


class PromptBuilder:

    def build(self, question):
        stats = detection_manager.snapshot()
        memory = scene_memory.snapshot()
        detections = vision_engine.get_detections()
        frame = vision_engine.get_frame()
        camera = camera_client.snapshot()
        
        logger.info("=" * 60)
        logger.info("HALO Vision Snapshot")
        logger.info(detections)
        logger.info("=" * 60)

        persons = len(detections)

        lines = []

        lines.append("You are HALO.")
        lines.append("You are the AI assistant of NoorBrain.")
        lines.append("Answer naturally and briefly.")
        lines.append("")

        lines.append("Current System State:")
        lines.append(f"Camera Connected : {camera['connected']}")
        lines.append(f"Camera FPS : {camera['fps']}")
        lines.append(f"Frames Processed : {stats['frame']}")
        lines.append(f"Persons Visible : {persons}")
        lines.append("")

        lines.append("Live Vision:")
        lines.append(f"Persons Detected : {persons}")
        lines.append(f"Total Detections : {stats.get('total', 0)}")
        lines.append("")

        lines.append("Current Detections:")
        
        if detections:
            for detection in detections:
                label = detection.get("label", "object")
                zone = detection.get("zone", "Unknown")
                confidence = detection.get("confidence", 0)

                lines.append(
                    f"- {label} "
                    f"in {zone} "
                    f"(confidence {confidence:.2f})"
                )
        else:
            lines.append("- No detections")
        
        lines.append("")
        lines.append("Scene Memory:")

        scene = scene_memory.snapshot()

        if scene:
            now = time.time()
            for label, person in scene.items():
                seconds = round(now - person["first_seen"], 1)
                lines.append(
                    f"- {label} "
                    f"in {person['zone']} "
                    f"for {seconds} seconds "
                    f"(confidence {person['confidence']:.2f})"
                )
        else:
            lines.append("- No remembered people")

        lines.append("")
        lines.append("Long Term Event History:")

        history = database.history_text()

        if history:
            lines.append(history)
        else:
            lines.append("No stored events.")

        lines.append("")
        lines.append("Person History:")

        history = person_history.snapshot()

        if history:
            for pid, journey in history.items():
                zones = [step["zone"] for step in journey]
                lines.append(
                    f"Person {pid}: "
                    + " -> ".join(zones)
                )
        else:
            lines.append("No history.")

        lines.append("")

        lines.append(f"User Question: {question}")
        lines.append("")

        lines.append("Reply in one or two short sentences.")

        return "\n".join(lines)


prompt_builder = PromptBuilder()
