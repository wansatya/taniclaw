"""TaniClaw Tool Executor — executes validated actions and logs them."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger("taniclaw.tools")


class ToolExecutor:
    """Executes validated actions. All actions are logged.

    Level 1 (default): instruction only — no physical execution.
    Level 2 (opt-in): digital execution (APIs, notifications).

    LLM cannot execute — only suggest. Security guard validates.
    """

    def __init__(self, memory, notification):
        self.memory = memory
        self.notification = notification
        self._registry: dict[str, Callable] = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tool functions."""
        self._registry = {
            "water": self._tool_water,
            "skip_water": self._tool_skip_water,
            "fertilize": self._tool_fertilize,
            "harvest": self._tool_harvest,
            "notify": self._tool_notify,
            "alert": self._tool_alert,
            "log": self._tool_log,
        }

    def execute(self, plant_id: uuid.UUID, action: dict) -> dict:
        """Execute a single action for a plant.

        Steps:
        1. Look up tool function from registry
        2. Execute the tool
        3. Create action record in memory
        4. Add to history
        5. Return result
        """
        action_type = action.get("type", "log")
        tool_fn = self._registry.get(action_type, self._tool_log)

        try:
            result = tool_fn(plant_id, action)
            # Record in memory
            action_record = self.memory.create_action({
                "plant_id": plant_id,
                "action_type": action_type,
                "description": action.get("description", ""),
                "source": action.get("source", "rules"),
                "status": "executed",
                "executed_at": datetime.now(timezone.utc),
            })
            # Add to history
            self.memory.add_history(plant_id, "action", {
                "action_id": str(action_record.id),
                "action_type": action_type,
                "description": action.get("description", ""),
                "source": action.get("source", "rules"),
                "result": result,
            })
            logger.info(f"Executed action {action_type!r} for plant {plant_id}: {action.get('description', '')[:60]}")
            return {"status": "ok", "action_type": action_type, "action_id": str(action_record.id), **result}
        except Exception as e:
            logger.error(f"Tool execution failed for {action_type!r}: {e}")
            # Still record the failed attempt
            self.memory.create_action({
                "plant_id": plant_id,
                "action_type": action_type,
                "description": action.get("description", ""),
                "source": action.get("source", "rules"),
                "status": "skipped",
            })
            return {"status": "error", "action_type": action_type, "error": str(e)}

    def _tool_water(self, plant_id: uuid.UUID, params: dict) -> dict:
        """Record watering action — Level 1: instruction only."""
        amount_ml = params.get("amount_ml", 200)
        logger.info(f"[WATER] Plant {plant_id}: {amount_ml}ml — {params.get('description', '')}")
        return {"amount_ml": amount_ml, "instruction": params.get("description", "")}

    def _tool_skip_water(self, plant_id: uuid.UUID, params: dict) -> dict:
        """Record skip watering with reason."""
        logger.info(f"[SKIP WATER] Plant {plant_id}: {params.get('description', '')}")
        return {"skipped": True, "reason": params.get("description", "")}

    def _tool_fertilize(self, plant_id: uuid.UUID, params: dict) -> dict:
        """Record fertilization action."""
        amount_grams = params.get("amount_grams", 5)
        fertilizer_type = params.get("fertilizer_type", "NPK")
        logger.info(f"[FERTILIZE] Plant {plant_id}: {amount_grams}g {fertilizer_type}")
        return {
            "amount_grams": amount_grams,
            "fertilizer_type": fertilizer_type,
            "instruction": params.get("description", ""),
        }

    def _tool_harvest(self, plant_id: uuid.UUID, params: dict) -> dict:
        """Record harvest action."""
        logger.info(f"[HARVEST] Plant {plant_id}: {params.get('description', '')}")
        return {"instruction": params.get("description", ""), "harvest_triggered": True}

    def _tool_notify(self, plant_id: uuid.UUID, params: dict) -> dict:
        """Send notification to user (Level 2: actual notification if configured)."""
        message = params.get("description", "")
        logger.info(f"[NOTIFY] Plant {plant_id}: {message}")
        # Note: actual async send happens in core.py cycle
        return {"message": message, "channel": "configured_channels"}

    def _tool_alert(self, plant_id: uuid.UUID, params: dict) -> dict:
        """Send high-priority alert to user."""
        message = params.get("description", "")
        logger.warning(f"[ALERT] Plant {plant_id}: {message}")
        return {"message": message, "priority": "high"}

    def _tool_log(self, plant_id: uuid.UUID, params: dict) -> dict:
        """Log activity to history."""
        message = params.get("description", "Daily cycle completed")
        logger.info(f"[LOG] Plant {plant_id}: {message}")
        return {"logged": True, "message": message}
