"""TaniClaw Knowledge Base — loads plant YAML files."""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger("taniclaw.knowledge")

_DEFAULT_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class KnowledgeBase:
    """Loads and queries plant knowledge from YAML files."""

    def __init__(self, knowledge_dir: str | Path | None = None):
        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else _DEFAULT_KNOWLEDGE_DIR
        self._plants: dict[str, dict] = {}
        self._diseases: dict[str, dict] = {}
        self._patterns: dict[str, dict] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all YAML knowledge files."""
        plants_dir = self.knowledge_dir / "plants"
        if plants_dir.exists():
            for path in plants_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(path.read_text())
                    if data and "plant_type" in data:
                        self._plants[data["plant_type"]] = data
                        logger.debug(f"Loaded plant knowledge: {data['plant_type']}")
                except Exception as e:
                    logger.error(f"Failed to load plant knowledge {path}: {e}")

        diseases_dir = self.knowledge_dir / "diseases"
        if diseases_dir.exists():
            for path in diseases_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(path.read_text())
                    if data:
                        self._diseases[path.stem] = data
                except Exception as e:
                    logger.error(f"Failed to load disease knowledge {path}: {e}")

        patterns_dir = self.knowledge_dir / "patterns"
        if patterns_dir.exists():
            for path in patterns_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(path.read_text())
                    if data:
                        self._patterns[path.stem] = data
                except Exception as e:
                    logger.error(f"Failed to load pattern knowledge {path}: {e}")

        logger.info(f"Knowledge base loaded: {len(self._plants)} plants, {len(self._diseases)} disease files, {len(self._patterns)} pattern files")

    def get_supported_plants(self) -> list[str]:
        """Return list of supported plant types."""
        return list(self._plants.keys())

    def get_plant_info(self, plant_type: str) -> dict | None:
        """Get full knowledge for a plant type."""
        return self._plants.get(plant_type)

    def get_stage_info(self, plant_type: str, stage: str) -> dict | None:
        """Get info for a specific lifecycle stage."""
        plant = self._plants.get(plant_type)
        if not plant:
            return None
        for s in plant.get("lifecycle", {}).get("stages", []):
            if s["name"] == stage:
                return s
        return None

    def get_watering_info(self, plant_type: str, stage: str) -> dict | None:
        """Get watering schedule for a plant at a given stage."""
        plant = self._plants.get(plant_type)
        if not plant:
            return None
        watering = plant.get("watering", {})
        stage_info = watering.get("adjust_by_stage", {}).get(stage)
        return stage_info

    def get_fertilizer_schedule(self, plant_type: str, stage: str) -> list[dict]:
        """Get fertilizer schedule for a plant at a given stage."""
        plant = self._plants.get(plant_type)
        if not plant:
            return []
        return [
            entry
            for entry in plant.get("fertilizer", {}).get("schedule", [])
            if entry.get("stage") == stage
        ]

    def get_disease_info(self, plant_type: str) -> list[dict]:
        """Get common diseases for a plant type."""
        plant = self._plants.get(plant_type)
        if not plant:
            return []
        return plant.get("diseases", {}).get("common", [])

    def get_expected_stage(self, plant_type: str, days_since_planting: int) -> str:
        """Determine expected lifecycle stage based on days since planting."""
        plant = self._plants.get(plant_type)
        if not plant:
            return "seed"
        stages = plant.get("lifecycle", {}).get("stages", [])
        elapsed = 0
        for stage in stages:
            duration = stage.get("duration_days", [7, 14])
            max_duration = duration[1] if len(duration) > 1 else duration[0]
            elapsed += max_duration
            if days_since_planting <= elapsed:
                return stage["name"]
        return stages[-1]["name"] if stages else "harvest"

    def get_stage_instructions(self, plant_type: str, stage: str) -> list[str]:
        """Get instructions for a specific lifecycle stage."""
        info = self.get_stage_info(plant_type, stage)
        if not info:
            return []
        return info.get("instructions", [])

    def get_stage_duration(self, plant_type: str, stage: str) -> tuple[int, int]:
        """Return (min_days, max_days) for a given stage."""
        info = self.get_stage_info(plant_type, stage)
        if not info:
            return (7, 14)
        duration = info.get("duration_days", [7, 14])
        return (duration[0], duration[1] if len(duration) > 1 else duration[0])

    def get_harvest_info(self, plant_type: str) -> dict:
        """Get harvest indicators and timing."""
        plant = self._plants.get(plant_type)
        if not plant:
            return {}
        return plant.get("harvest", {})
