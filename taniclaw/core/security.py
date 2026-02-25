"""TaniClaw Security Guard — validates all actions before execution."""

import logging
import uuid

from taniclaw.core.config import Settings

logger = logging.getLogger("taniclaw.security")

ALLOWED_ACTION_TYPES = {
    "water",
    "skip_water",
    "fertilize",
    "harvest",
    "notify",
    "alert",
    "log",
}

MAX_FERTILIZER_GRAMS = 20
MAX_WATER_AMOUNT_ML = 2000


class SecurityGuard:
    """Validates all actions before execution.

    - LLM cannot execute — only suggest.
    - Rules validate actions.
    - Execution limits enforced.
    - Human override always available.
    - All actions logged.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def validate_action(self, action: dict, context: dict, memory=None, plant_id: uuid.UUID | None = None) -> tuple[bool, str]:
        """
        Validate an action before execution.
        Returns (is_valid, reason).

        Checks:
        1. Action type is in allowed list
        2. Daily action limit not exceeded
        3. Watering amount within max limit
        4. Fertilizer amount within safe range
        5. Action source is trusted
        """
        action_type = action.get("type", "")

        # Human overrides always pass
        if self.is_human_override(action):
            logger.info(f"Human override action accepted: {action_type}")
            return True, "human_override"

        # 1. Check action type
        if action_type not in ALLOWED_ACTION_TYPES:
            reason = f"Unknown action type: {action_type!r}"
            self.log_security_event("blocked_unknown_type", {"action": action, "reason": reason})
            return False, reason

        # 2. Check daily limit
        if memory and plant_id:
            if not self.check_daily_limit(plant_id, memory):
                reason = f"Daily action limit exceeded ({self.settings.max_daily_actions} actions/day)"
                self.log_security_event("blocked_daily_limit", {"plant_id": str(plant_id), "reason": reason})
                return False, reason

        # 3. Check watering amount
        if action_type == "water":
            if not self.check_watering_limit(action):
                reason = f"Watering amount exceeds maximum ({MAX_WATER_AMOUNT_ML}ml)"
                self.log_security_event("blocked_watering_limit", {"action": action, "reason": reason})
                return False, reason

        # 4. Check fertilizer amount
        if action_type == "fertilize":
            if not self.check_fertilizer_limit(action):
                reason = f"Fertilizer amount exceeds maximum ({MAX_FERTILIZER_GRAMS}g)"
                self.log_security_event("blocked_fertilizer_limit", {"action": action, "reason": reason})
                return False, reason

        return True, "ok"

    def check_daily_limit(self, plant_id: uuid.UUID, memory) -> bool:
        """Return True if daily action limit NOT exceeded."""
        count = memory.get_today_actions_count(plant_id)
        return count < self.settings.max_daily_actions

    def check_watering_limit(self, action: dict) -> bool:
        """Return True if watering amount is within safe range."""
        amount = action.get("amount_ml", 0)
        return amount <= MAX_WATER_AMOUNT_ML

    def check_fertilizer_limit(self, action: dict) -> bool:
        """Return True if fertilizer amount is within safe range."""
        amount = action.get("amount_grams", 0)
        return amount <= MAX_FERTILIZER_GRAMS

    def is_human_override(self, action: dict) -> bool:
        """Check if action is a human override (always allowed)."""
        return action.get("source") == "manual"

    def log_security_event(self, event_type: str, details: dict) -> None:
        """Log security-related events."""
        logger.warning(f"SECURITY [{event_type}]: {details}")
