"""
============================================================
Project : NoorBrain
Module  : Reminder Engine
Version : 0.1.0
Purpose : Plays a spoken reminder when a person enters a zone.
          Uses offline TTS (espeak via pyttsx3).
============================================================
"""

import threading
import queue
import time
from pathlib import Path

import pyttsx3
import yaml

from shared.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REMINDERS_FILE = PROJECT_ROOT / "config" / "reminders.yaml"


class ReminderEngine:

    def __init__(self):

        self.reminders = {}
        self.cooldown_seconds = 30

        self.load_reminders()

        self.last_zone = None
        self.last_played = {}

        self.speech_queue = queue.Queue()

        self.thread = threading.Thread(
            target=self._worker,
            daemon=True
        )
        self.thread.start()

    def load_reminders(self):

        if not REMINDERS_FILE.exists():
            self.reminders = {}
            return

        with open(REMINDERS_FILE, "r") as file:
            data = yaml.safe_load(file) or {}

        self.reminders = data.get("reminders", {}) or {}
        self.cooldown_seconds = data.get("cooldown_seconds", 30)

        logger.info(f"Loaded {len(self.reminders)} reminders")

    def _worker(self):

        engine = pyttsx3.init()
        engine.setProperty("rate", 150)

        while True:

            text = self.speech_queue.get()

            try:
                engine.say(text)
                engine.runAndWait()

            except Exception as e:
                logger.error(f"TTS Error: {e}")

    def on_zone_detected(self, zone_name):

        if not zone_name or zone_name == "Unknown":
            return

        if zone_name == self.last_zone:
            return

        now = time.time()
        last_time = self.last_played.get(zone_name, 0)

        if now - last_time < self.cooldown_seconds:
            self.last_zone = zone_name
            return

        message = self.reminders.get(zone_name)

        if message:
            logger.info(f"Reminder triggered: {zone_name} -> \"{message}\"")
            self.speech_queue.put(message)
            self.last_played[zone_name] = now

        self.last_zone = zone_name


reminder_engine = ReminderEngine()
