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
import threading
import time
import uuid

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
        self._cooldown_file = self.rules_file.parent.parent / "data" / "reminder_cooldowns_v16.json"

        self._load()
        self._load_cooldowns()

    # --------------------------------------------------
    def _load_cooldowns(self):
        """Keep reminder suppression active across NoorBrain restarts."""
        try:
            payload = json.loads(self._cooldown_file.read_text(encoding="utf-8"))
            values = payload.get("last_fired", {})
            if isinstance(values, dict):
                self._last_fired = {
                    str(key): float(value)
                    for key, value in values.items()
                    if float(value) > 0
                }
        except Exception:
            self._last_fired = {}

    # --------------------------------------------------
    def _save_cooldowns(self):
        try:
            self._cooldown_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._cooldown_file.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    {"version": 1, "last_fired": self._last_fired},
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._cooldown_file)
        except Exception:
            pass

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
            "zone_occupied",
            "zone_exited",
            "moved_zone",
            "left_zone",
            "stayed",
            "disappeared",
            "scheduled_time",
            "prayer_time",
            "before_prayer",
            "after_prayer",
            "habit_condition",
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

        target_node = str(rule.get("target_node") or "").strip() or None
        action_type = str(rule.get("action_type") or ("media" if media_id else "tts")).strip().lower()
        if action_type not in {"tts", "media", "dua", "azkar", "reminder_audio", "notification", "device_action", "scene", "routine"}:
            action_type = "tts"
        days = rule.get("days") if isinstance(rule.get("days"), list) else []

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
            "action_type": action_type,
            "target_node": target_node,
            "days": [str(day).strip().lower() for day in days if str(day).strip()],
            "time_start": str(rule.get("time_start") or "").strip() or None,
            "time_end": str(rule.get("time_end") or "").strip() or None,
            "require_target_online": bool(rule.get("require_target_online", True)),
            "last_triggered": rule.get("last_triggered"),
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

            if rule["action_type"] in {"tts", "media", "dua", "azkar", "reminder_audio"} and not rule.get("target_node"):
                raise ValueError("A target Raspberry Pi speaker is required")

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

                if updated["action_type"] in {"tts", "media", "dua", "azkar", "reminder_audio"} and not updated.get("target_node"):
                    raise ValueError("A target Raspberry Pi speaker is required")

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
            self._last_fired = {
                key: value
                for key, value in self._last_fired.items()
                if not key.startswith(f"{rule_id}|")
            }
            self._save_cooldowns()

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

        days = rule.get("days") or []
        if days and datetime.now().strftime("%A").lower() not in days:
            return False

        start = rule.get("time_start")
        end = rule.get("time_end")
        if start and end:
            current = datetime.now().strftime("%H:%M")
            if not (start <= current <= end):
                return False

        return True

    # --------------------------------------------------
    def _cooldown_key(self, rule, event):
        # YOLO tracker IDs are temporary and change after a short detection
        # loss.  They must never be used as a reminder identity.  Use a real
        # face identity when one is supplied; otherwise protect the complete
        # room/presence session.  This prevents motion from replaying audio.
        stable_person = (
            event.get("recognized_person_id")
            or event.get("identity_id")
            or event.get("person_uuid")
        )
        zone = event.get("zone") or "single-camera-room"
        subject = f"person:{stable_person}" if stable_person else "room-presence"
        return f"{rule['id']}|{subject}|{zone}"

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
    # --------------------------------------------------
    def _fire(self, rule, event, test=False):
        now = time.time()

        message = self._render_message(
            rule["message"],
            event
        )

        playback_result = {"playback_status": "not_requested", "laptop_playback": False}
        action_type = rule.get("action_type") or ("media" if rule.get("media_id") else "tts")
        if action_type in {"tts", "media", "dua", "azkar", "reminder_audio"}:
            try:
                from services.playback_router import playback_router
                routed = playback_router.play({
                    "target_node": rule.get("target_node"),
                    "type": action_type,
                    "content": message,
                    "media_id": rule.get("media_id"),
                })
                playback_result = {"playback_status": "played", "playback": routed, "laptop_playback": False}
            except Exception as error:
                playback_result = {"playback_status": "failed", "playback_error": str(error), "laptop_playback": False}

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
            "action_type": action_type,
            "target_node": rule.get("target_node"),
            **playback_result,
        }

        self._history.appendleft(record)

        if not test:
            key = self._cooldown_key(
                rule,
                event
            )

            self._last_fired[key] = now
            self._save_cooldowns()
            with self._lock:
                for stored in self._rules:
                    if stored["id"] == rule["id"]:
                        stored["last_triggered"] = now
                        break
                self._save()

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
            "presence_guard": "active",
            "cooldown_identity": "recognized-person-or-room-session",
            "electronic_voice": False,
            "rules": self.list_rules(),
            "rule_count": len(
                self.list_rules()
            ),
            "history": self.history(
                history_limit
            )
        }


reminder_rules = ReminderRulesEngine()
