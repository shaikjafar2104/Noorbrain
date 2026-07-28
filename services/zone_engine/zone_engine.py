"""
============================================================
Project : NoorBrain
Module  : Zone Engine
Version : 0.2.0
Purpose : Maps a bounding box (person location) to a named zone.
          Zones can be loaded from file and saved from dashboard.
============================================================
"""

import yaml
from pathlib import Path

from shared.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ZONES_FILE = PROJECT_ROOT / "config" / "zones.yaml"


class ZoneEngine:

    def __init__(self):

        self.zones = []
        self.load_zones()

    def load_zones(self):

        if not ZONES_FILE.exists():
            self.zones = []
            return

        with open(ZONES_FILE, "r") as file:
            data = yaml.safe_load(file) or {}

        self.zones = data.get("zones", [])

        logger.info(f"Loaded {len(self.zones)} zones")

    def save_zones(self, zones):

        data = {"zones": zones}

        with open(ZONES_FILE, "w") as file:
            yaml.dump(data, file, default_flow_style=False)

        self.zones = zones

        logger.info(f"Saved {len(zones)} zones")

    def get_zone_for_box(self, box):
        """
        box = [x1, y1, x2, y2] of the detected person.
        Uses the center point of the box to decide the zone.
        """

        x1, y1, x2, y2 = box

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        for zone in self.zones:

            if (zone["x1"] <= center_x <= zone["x2"] and
                    zone["y1"] <= center_y <= zone["y2"]):

                return zone["name"]

        return "Unknown"

    def get_all_zones(self):
        return self.zones


zone_engine = ZoneEngine()
