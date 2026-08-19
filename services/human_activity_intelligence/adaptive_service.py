"""Adaptive Rule Intelligence — connects HAI events to approved reminder rules.

Pipeline:
  Human Activity Intelligence -> Activity observations -> Pattern learner
  -> Rule proposals -> User approval -> services/reminder_rules

Does NOT execute actions directly. Only creates proposals and, on approval,
converts them to entries in the existing reminder_rules system.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from .store import activity_store, ActivityStore

# Suggestion cooldown: once a suggestion is rejected, don't propose the same
# pattern-group again for this many seconds.
DEFAULT_COOLDOWN_SECONDS = 72 * 3600  # 72 hours = 3 days


class AdaptiveRuleIntelligence:
    """Consumes HAI activity events, learns patterns, and proposes rules.

    The actual proposal/rule engine logic lives in pattern_learner.py
    (rebuild_patterns, generate_rule_suggestions). This class orchestrates
    the periodic rebuild cycle and the approval -> reminder_rules bridge.
    """

    def __init__(self, store: ActivityStore | None = None) -> None:
        self._store = store or activity_store
        self._lock = threading.RLock()
        self._started_at = time.time()

    # ------------------------------------------------------------------
    # Health / status
    # ------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Return health + summary status."""
        settings = self._store.get_all_settings()
        return {
            "status": "healthy",
            "service": "adaptive_rule_intelligence",
            "version": "1.0.0",
            "learning_enabled": settings.get("learning_enabled", "true") in {"1", "true", "yes"},
            "automatic_rule_creation": settings.get("automatic_rule_creation", "false") in {"1", "true", "yes"},
            "pattern_count": self._store.pattern_count(),
            "suggestion_count": self._store.suggestion_count(),
            "event_count": self._store.event_count(),
            "snapshot_enabled": settings.get("snapshot_enabled", "false") in {"1", "true", "yes"},
        }

    # ------------------------------------------------------------------
    # Pattern learning cycle
    # ------------------------------------------------------------------

    def rebuild_patterns(self) -> dict[str, Any]:
        """Trigger a pattern rebuild from recent activity events."""
        from .pattern_learner import rebuild_patterns
        return rebuild_patterns(store=self._store)

    def generate_suggestions(self) -> dict[str, Any]:
        """Generate rule suggestions from learned patterns.

        Never enables rules automatically.
        """
        from .pattern_learner import generate_rule_suggestions
        return generate_rule_suggestions(store=self._store)

    def learn(self) -> dict[str, Any]:
        """Run a full learning cycle: rebuild patterns + generate suggestions."""
        patterns_result = self.rebuild_patterns()
        suggestions_result = self.generate_suggestions()
        return {
            "status": "ok",
            "patterns": patterns_result,
            "suggestions": suggestions_result,
        }

    # ------------------------------------------------------------------
    # Proposal approval -> reminder rules
    # ------------------------------------------------------------------

    def approve_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        """Approve a suggestion and create a rule in the existing reminder engine.

        This is the ONLY path through which adaptive proposals become executable.
        The adaptive intelligence does NOT fire reminders itself -- it creates
        the rule, and the existing reminder_rules engine handles execution.
        """
        suggestion = self._store.get_suggestion(suggestion_id)
        if suggestion is None:
            return {"status": "error", "detail": "suggestion not found"}

        if suggestion.get("user_approved"):
            return {"status": "already_approved", "suggestion": suggestion}

        # Mark as approved in the activity store
        approved = self._store.approve_suggestion(suggestion_id)
        if approved is None:
            return {"status": "error", "detail": "failed to approve suggestion"}

        # Create a rule in the existing reminder_rules system
        rule_created = self._create_reminder_rule(suggestion)

        return {
            "status": "approved",
            "suggestion": approved,
            "rule_created": rule_created is not None,
            "rule": rule_created,
        }

    def _create_reminder_rule(self, suggestion: dict[str, Any]) -> dict[str, Any] | None:
        """Create a rule in services/reminder_rules from an approved suggestion.

        Uses the existing reminder_rules.create_rule() API.
        Returns the created rule dict, or None on failure.
        """
        try:
            from services.reminder_rules import reminder_rules

            rule_name = suggestion.get("rule_name") or "Auto-generated rule"
            rule_trigger = suggestion.get("rule_trigger") or "entered_zone"
            rule_zone = suggestion.get("rule_zone") or None
            rule_message = suggestion.get("rule_message") or "Activity detected."
            rule_action_type = suggestion.get("rule_action_type") or "notification"
            rule_cooldown = int(suggestion.get("rule_cooldown_seconds", 1800))
            rule_days = suggestion.get("rule_days") or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            suggestion_id = suggestion.get("id")

            # Check for duplicate rule before creating
            existing_rules = reminder_rules.list_rules()
            duplicate = any(
                r.get("name") == rule_name and r.get("trigger") == rule_trigger
                for r in existing_rules
            )
            if duplicate:
                for r in existing_rules:
                    if r.get("name") == rule_name and r.get("trigger") == rule_trigger:
                        self._store.set_setting(
                            f"rule_linked:{suggestion_id}",
                            str(r.get("id")),
                        )
                        return r

            # Create rule using existing create_rule(data dict) API
            rule_data = {
                "name": rule_name,
                "trigger": rule_trigger,
                "zone": rule_zone,
                "message": rule_message,
                "action_type": rule_action_type,
                "cooldown_seconds": rule_cooldown,
                "days": rule_days,
            }
            created = reminder_rules.create_rule(rule_data)
            if created:
                self._store.set_setting(
                    f"rule_linked:{suggestion_id}",
                    str(created.get("id")),
                )
                return created

            return None
        except Exception:
            return None

    def reject_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        """Reject a suggestion and apply cooldown."""
        result = self._store.reject_suggestion(suggestion_id)
        if result is None:
            return {"status": "error", "detail": "suggestion not found"}

        # Apply cooldown for this pattern type + zone
        pattern_id = result.get("pattern_id")
        if pattern_id:
            self._store.set_setting(
                f"cooldown:{pattern_id}",
                str(time.time() + DEFAULT_COOLDOWN_SECONDS),
            )

        return {"status": "rejected", "suggestion": result}

    # ------------------------------------------------------------------
    # Pattern management
    # ------------------------------------------------------------------

    def patterns(self, person_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        items = self._store.list_patterns(person_id=person_id, limit=limit)
        return {"status": "ok", "count": len(items), "patterns": items}

    def pattern_count(self) -> dict[str, Any]:
        return {"status": "ok", "count": self._store.pattern_count()}

    def suggestions(self, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        items = self._store.list_suggestions(status=status, limit=limit)
        return {"status": "ok", "count": len(items), "suggestions": items}

    def suggestion_count(self) -> dict[str, Any]:
        return {"status": "ok", "count": self._store.suggestion_count()}

    def get_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        item = self._store.get_suggestion(suggestion_id)
        if item is None:
            return {"status": "not_found", "suggestion_id": suggestion_id}
        return {"status": "ok", "suggestion": item}

    def dismiss_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        result = self._store.dismiss_suggestion(suggestion_id)
        if result is None:
            return {"status": "error", "detail": "suggestion not found"}
        return {"status": "dismissed", "suggestion": result}

    def snooze_suggestion(self, suggestion_id: str, minutes: int = 30) -> dict[str, Any]:
        result = self._store.snooze_suggestion(suggestion_id, minutes)
        if result is None:
            return {"status": "error", "detail": "suggestion not found"}
        return {"status": "snoozed", "suggestion": result}

    def never_suggest(self, suggestion_id: str) -> dict[str, Any]:
        result = self._store.never_suggest(suggestion_id)
        if result is None:
            return {"status": "error", "detail": "suggestion not found"}
        return {"status": "never_suggest", "suggestion": result}


# ------------------------------------------------------------------
# Module-level singleton (used by routes)
# ------------------------------------------------------------------

adaptive_rule_intelligence = AdaptiveRuleIntelligence()
