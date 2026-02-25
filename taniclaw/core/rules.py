"""TaniClaw Rules Engine — evaluates YAML rules against plant context."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger("taniclaw.rules")

_DEFAULT_RULES_DIR = Path(__file__).parent.parent / "rules"


class RulesEngine:
    """Evaluates YAML rules against plant context to produce actions.

    No LLM required — pure rule-based decision making.
    Rules are sorted by priority (higher number = evaluated first).
    All rules conditions use AND logic.
    """

    def __init__(self, rules_dir: str | Path | None = None):
        self.rules_dir = Path(rules_dir) if rules_dir else _DEFAULT_RULES_DIR
        self.rules: list[dict] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Load all .yaml rule files, merge, and sort by priority descending."""
        all_rules = []
        if self.rules_dir.exists():
            for path in sorted(self.rules_dir.glob("*.yaml")):
                try:
                    data = yaml.safe_load(path.read_text())
                    if data and "rules" in data:
                        all_rules.extend(data["rules"])
                        logger.debug(f"Loaded {len(data['rules'])} rules from {path.name}")
                except Exception as e:
                    logger.error(f"Failed to load rules from {path}: {e}")
        # Sort by priority descending (100 = critical first)
        self.rules = sorted(all_rules, key=lambda r: r.get("priority", 10), reverse=True)
        logger.info(f"Rules engine loaded: {len(self.rules)} rules")

    def evaluate(self, context: dict) -> list[dict]:
        """
        Evaluate all rules against the given context.

        Context dict contains:
            - plant_type: str
            - plant_state: str
            - days_since_planting: int
            - days_in_state: int
            - days_since_last_water: int
            - days_since_last_fertilize: int
            - today_rainfall_mm: float
            - temp_max: float
            - temp_min: float
            - humidity: float
            - growing_method: str (optional)
            - soil_condition: str (optional)

        Returns list of matched actions sorted by priority (already sorted from load).
        """
        matched: list[dict] = []
        for rule in self.rules:
            if self._check_rule(rule, context):
                action = rule.get("action", {}).copy()
                action["rule_id"] = rule.get("id", "unknown")
                action["rule_name"] = rule.get("name", "")
                action["priority"] = rule.get("priority", 10)
                matched.append(action)
                logger.debug(f"Rule matched: {rule.get('id')} → {action.get('type')}")
        return matched

    def _check_condition(self, condition: dict, context: dict) -> bool:
        """Check a single condition against context."""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        actual = context.get(field)

        if actual is None:
            return False

        match operator:
            case "eq":
                return actual == value
            case "neq":
                return actual != value
            case "gt":
                return actual > value
            case "gte":
                return actual >= value
            case "lt":
                return actual < value
            case "lte":
                return actual <= value
            case "in":
                return actual in value
            case "not_in":
                return actual not in value
            case "contains":
                return value in str(actual)
            case _:
                logger.warning(f"Unknown operator: {operator!r}")
                return False

    def _check_rule(self, rule: dict, context: dict) -> bool:
        """All conditions must match (AND logic)."""
        conditions = rule.get("conditions", [])
        if not conditions:
            return False
        return all(self._check_condition(c, context) for c in conditions)

    def get_rule_by_id(self, rule_id: str) -> dict | None:
        """Retrieve a rule by its ID."""
        for rule in self.rules:
            if rule.get("id") == rule_id:
                return rule
        return None
