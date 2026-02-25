"""TaniClaw State Engine — plant lifecycle state machine."""

import logging
from datetime import date, datetime, timezone
from enum import Enum

logger = logging.getLogger("taniclaw.state")


class PlantState(str, Enum):
    SEED = "seed"
    GERMINATION = "germination"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    HARVEST = "harvest"
    DORMANT = "dormant"
    DEAD = "dead"


# Valid state transitions
TRANSITIONS: dict[PlantState, list[PlantState]] = {
    PlantState.SEED: [PlantState.GERMINATION, PlantState.DEAD],
    PlantState.GERMINATION: [PlantState.VEGETATIVE, PlantState.DEAD],
    PlantState.VEGETATIVE: [PlantState.FLOWERING, PlantState.HARVEST, PlantState.DEAD],
    PlantState.FLOWERING: [PlantState.HARVEST, PlantState.VEGETATIVE, PlantState.DEAD],
    PlantState.HARVEST: [PlantState.DORMANT, PlantState.DEAD],
    PlantState.DORMANT: [PlantState.VEGETATIVE],
    PlantState.DEAD: [],
}

# Plants without a flowering stage go directly to harvest
PLANTS_WITHOUT_FLOWERING = {"spinach", "lettuce", "hydroponic"}


class StateEngine:
    """Manages plant lifecycle state transitions.

    Rules-first approach — no LLM required.
    Uses knowledge base for expected stage durations.
    """

    def __init__(self, knowledge):
        self.knowledge = knowledge

    def get_current_state(self, plant) -> PlantState:
        """Return current PlantState enum for a plant."""
        try:
            return PlantState(plant.current_state)
        except ValueError:
            logger.warning(f"Unknown state {plant.current_state!r} for plant {plant.id} — defaulting to SEED")
            return PlantState.SEED

    def get_days_since_planting(self, plant) -> int:
        """Return number of days since planting date."""
        today = date.today()
        delta = today - plant.plant_date
        return max(0, delta.days)

    def get_days_in_current_state(self, plant) -> int:
        """Return number of days in the current lifecycle state."""
        if plant.state_changed_at is None:
            return self.get_days_since_planting(plant)
        now = datetime.now(timezone.utc)
        # Handle naive datetime
        if plant.state_changed_at.tzinfo is None:
            changed = plant.state_changed_at.replace(tzinfo=timezone.utc)
        else:
            changed = plant.state_changed_at
        delta = now - changed
        return max(0, delta.days)

    def can_transition(self, current: PlantState, target: PlantState) -> bool:
        """Check if a transition from current to target state is valid."""
        return target in TRANSITIONS.get(current, [])

    def should_transition(self, plant) -> PlantState | None:
        """
        Determine if a plant should transition to the next stage.

        Logic:
        1. Get current state and days in that state.
        2. Look up expected max duration from knowledge base.
        3. If days exceed max duration, recommend transition.
        4. Return recommended new state, or None.

        No LLM required — pure time-based + knowledge-based logic.
        """
        current = self.get_current_state(plant)

        # Dead plants don't transition
        if current == PlantState.DEAD:
            return None

        days_in_state = self.get_days_in_current_state(plant)
        _, max_days = self.knowledge.get_stage_duration(plant.plant_type, current.value)

        if days_in_state < max_days:
            return None

        # Determine next state
        valid_next = TRANSITIONS.get(current, [])
        if not valid_next:
            return None

        # Skip flowering for plants without a flowering stage
        if plant.plant_type in PLANTS_WITHOUT_FLOWERING:
            filtered = [s for s in valid_next if s != PlantState.FLOWERING]
            valid_next = filtered if filtered else valid_next

        # Return the first valid transition (next in lifecycle)
        for candidate in valid_next:
            if candidate != PlantState.DEAD:
                return candidate

        return None

    def get_next_state(self, plant) -> PlantState | None:
        """Return the expected next state in the lifecycle."""
        current = self.get_current_state(plant)
        nexts = TRANSITIONS.get(current, [])
        for n in nexts:
            if n != PlantState.DEAD:
                return n
        return None
