"""
NoorBrain Reminder Rules Engine

Activity events:
- appeared
- entered_zone
- moved_zone
- left_zone
- stayed
- disappeared

Rules are stored in config/reminder_rules.json.
"""

from collections import deque
from datetime import datetime
from pathlib import Path
import json
import shutil
import subprocess
import threading
import time
import uuid

from services.media_library.media_manager import (
    MediaLibraryError,
    MediaNotFoundError,
    media_library,
)


class ReminderRulesEngine:

    def __init__(
        self,
        rules_file="config/reminder_rules.json",
        maximum_history=300
    ):
        self.rules_file = Path(rules_file)
        self.rules_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._lock = threading.RLock()
        self._rules = []
        self._history = deque(maxlen=maximum_history)
        self._last_fired = {}

        self._load()

    # --------------------------------------------------
    def _default_document(self):
        return {
            "version": 1,
            "rules": []
        }

    # --------------------------------------------------
    def _load(self):
        with self._lock:
            if not self.rules_file.exists():
                self._save()
                return

            try:
                document = json.loads(
                    self.rules_file.read_text(
                        encoding="utf-8"
                    )
                )

                rules = document.get("rules", [])

                if not isinstance(rules, list):
                    rules = []

                self._rules = [
                    self._normalise_rule(rule)
                    for rule in rules
                    if isinstance(rule, dict)
                ]

            except Exception:
                backup = self.rules_file.with_suffix(
                    ".invalid.json"
                )

                try:
                    shutil.copy2(
                        self.rules_file,
                        backup
                    )
                except Exception:
                    pass

                self._rules = []
                self._save()

    # --------------------------------------------------
    def _save(self):
        document = {
            "version": 1,
            "rules": self._rules
        }

        temporary = self.rules_file.with_suffix(
            ".tmp"
        )

        temporary.write_text(
            json.dumps(
                document,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        temporary.replace(self.rules_file)

    # --------------------------------------------------
    @staticmethod
    def _normalise_rule(rule):
        trigger = str(
            rule.get("trigger", "entered_zone")
        ).strip()

        if trigger not in {
            "appeared",
            "entered_zone",
            "moved_zone",
            "left_zone",
            "stayed",
            "disappeared"
        }:
            trigger = "entered_zone"

        zone = rule.get("zone")

        if zone is not None:
            zone = str(zone).strip() or None

        try:
            cooldown = max(
                0,
                int(rule.get("cooldown_seconds", 1800))
            )
        except (TypeError, ValueError):
            cooldown = 1800

        message = str(
            rule.get("message", "")
        ).strip()

        name = str(
            rule.get("name", "Reminder Rule")
        ).strip() or "Reminder Rule"

        media_id = rule.get("media_id")

        if media_id is not None:
            media_id = str(media_id).strip() or None

        return {
            "id": str(
                rule.get("id") or uuid.uuid4()
            ),
            "name": name,
            "enabled": bool(
                rule.get("enabled", True)
            ),
            "trigger": trigger,
            "zone": zone,
            "message": message,
            "cooldown_seconds": cooldown,
            "speak": bool(
                rule.get("speak", True)
            ),
            "media_id": media_id,
            "created_at": float(
                rule.get(
                    "created_at",
                    time.time()
                )
            )
        }

    # --------------------------------------------------
    def list_rules(self):
        with self._lock:
            return [
                dict(rule)
                for rule in self._rules
            ]

    # --------------------------------------------------
    def create_rule(self, data):
        with self._lock:
            rule = self._normalise_rule(data)

            if not rule["message"]:
                raise ValueError(
                    "Reminder message required"
                )

            self._rules.append(rule)
            self._save()

            return dict(rule)

    # --------------------------------------------------
    def update_rule(self, rule_id, data):
        with self._lock:
            for index, existing in enumerate(
                self._rules
            ):
                if existing["id"] != rule_id:
                    continue

                merged = dict(existing)
                merged.update(data)
                merged["id"] = existing["id"]
                merged["created_at"] = existing[
                    "created_at"
                ]

                updated = self._normalise_rule(
                    merged
                )

                if not updated["message"]:
                    raise ValueError(
                        "Reminder message required"
                    )

                self._rules[index] = updated
                self._save()

                return dict(updated)

        raise KeyError("Rule not found")

    # --------------------------------------------------
    def delete_rule(self, rule_id):
        with self._lock:
            original_count = len(self._rules)

            self._rules = [
                rule
                for rule in self._rules
                if rule["id"] != rule_id
            ]

            if len(self._rules) == original_count:
                raise KeyError("Rule not found")

            self._save()
            self._last_fired.pop(rule_id, None)

        return {
            "status": "deleted",
            "rule_id": rule_id
        }

    # --------------------------------------------------
    def toggle_rule(self, rule_id, enabled):
        return self.update_rule(
            rule_id,
            {
                "enabled": bool(enabled)
            }
        )

    # --------------------------------------------------
    @staticmethod
    def _event_zone(event):
        return event.get("zone")

    # --------------------------------------------------
    def _matches(self, rule, event):
        if not rule["enabled"]:
            return False

        if rule["trigger"] != event.get("type"):
            return False

        required_zone = rule.get("zone")

        if required_zone:
            event_zone = self._event_zone(event)

            if event_zone != required_zone:
                return False

        return True

    # --------------------------------------------------
    def _cooldown_key(self, rule, event):
        person_id = event.get(
            "person_id",
            "unknown"
        )

        zone = event.get("zone") or "none"

        return (
            rule["id"],
            str(person_id),
            str(zone)
        )

    # --------------------------------------------------
    def _cooldown_ready(self, rule, event):
        key = self._cooldown_key(rule, event)
        previous = self._last_fired.get(key)

        if previous is None:
            return True

        return (
            time.time() - previous
            >= rule["cooldown_seconds"]
        )

    # --------------------------------------------------
    @staticmethod
    def _render_message(template, event):
        values = {
            "person_id": event.get(
                "person_id",
                ""
            ),
            "zone": event.get("zone") or "",
            "previous_zone": (
                event.get("previous_zone")
                or ""
            ),
            "duration": event.get(
                "duration",
                ""
            ),
            "event": event.get(
                "type",
                ""
            )
        }

        try:
            return template.format(**values)
        except Exception:
            return template

    # --------------------------------------------------
    @staticmethod
    def _speak(message):
        commands = [
            ["espeak-ng", message],
            ["espeak", message]
        ]

        for command in commands:
            if shutil.which(command[0]):
                try:
                    subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    return {
                        "spoken": True,
                        "speaker": command[0]
                    }

                except Exception as error:
                    return {
                        "spoken": False,
                        "error": str(error)
                    }

        return {
            "spoken": False,
            "error": (
                "espeak-ng or espeak "
                "not installed"
            )
        }

    # --------------------------------------------------
    def _fire(self, rule, event, test=False):
        now = time.time()

        message = self._render_message(
            rule["message"],
            event
        )

        speech_result = {
            "spoken": False
        }

        media_result = {
            "media_played": False,
            "media_id": rule.get("media_id")
        }

        selected_media_id = rule.get("media_id")

        if selected_media_id:
            try:
                result = media_library.play_item(
                    selected_media_id
                )

                item = result.get("item") or {}

                media_result = {
                    "media_played": True,
                    "media_id": selected_media_id,
                    "media_name": (
                        item.get("display_name")
                        or item.get("name")
                        or item.get("original_filename")
                        or item.get("filename")
                        or "Selected audio"
                    ),
                    "media_player": result.get(
                        "player"
                    )
                }

            except (
                MediaLibraryError,
                MediaNotFoundError,
                KeyError,
                OSError
            ) as error:
                media_result = {
                    "media_played": False,
                    "media_id": selected_media_id,
                    "media_error": str(error)
                }

        elif rule.get("speak", True):
            speech_result = self._speak(message)

        record = {
            "reminder_id": str(uuid.uuid4()),
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "message": message,
            "trigger": event.get("type"),
            "person_id": event.get(
                "person_id"
            ),
            "zone": event.get("zone"),
            "previous_zone": event.get(
                "previous_zone"
            ),
            "timestamp": now,
            "time_text": datetime.fromtimestamp(
                now
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "test": bool(test),
            **speech_result,
            **media_result
        }

        self._history.appendleft(record)

        if not test:
            key = self._cooldown_key(
                rule,
                event
            )

            self._last_fired[key] = now

        return record

    # --------------------------------------------------
    def handle_event(self, event):
        fired = []

        with self._lock:
            rules = [
                dict(rule)
                for rule in self._rules
            ]

            for rule in rules:
                if not self._matches(
                    rule,
                    event
                ):
                    continue

                if not self._cooldown_ready(
                    rule,
                    event
                ):
                    continue

                fired.append(
                    self._fire(
                        rule,
                        event
                    )
                )

        return fired

    # --------------------------------------------------
    def test_rule(self, rule_id):
        with self._lock:
            rule = next(
                (
                    item
                    for item in self._rules
                    if item["id"] == rule_id
                ),
                None
            )

            if rule is None:
                raise KeyError("Rule not found")

            test_event = {
                "type": rule["trigger"],
                "person_id": 1,
                "zone": (
                    rule.get("zone")
                    or "Selected Zone"
                ),
                "previous_zone": (
                    "Previous Zone"
                ),
                "duration": 60,
                "timestamp": time.time()
            }

            return self._fire(
                rule,
                test_event,
                test=True
            )

    # --------------------------------------------------
    def history(self, limit=100):
        try:
            limit = max(
                1,
                min(int(limit), 300)
            )
        except (TypeError, ValueError):
            limit = 100

        with self._lock:
            return list(self._history)[:limit]

    # --------------------------------------------------
    def clear_history(self):
        with self._lock:
            self._history.clear()

        return {
            "status": "cleared"
        }

    # --------------------------------------------------
    def snapshot(self, history_limit=50):
        return {
            "status": "running",
            "rules": self.list_rules(),
            "rule_count": len(
                self.list_rules()
            ),
            "history": self.history(
                history_limit
            )
        }


reminder_rules = ReminderRulesEngine()
