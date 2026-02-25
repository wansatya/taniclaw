"""TaniClaw Core Agent Orchestrator — main execution loop."""

import logging
import uuid
from datetime import date

from taniclaw.core.config import Settings
from taniclaw.core.knowledge import KnowledgeBase
from taniclaw.core.state import StateEngine, PlantState
from taniclaw.core.rules import RulesEngine
from taniclaw.core.security import SecurityGuard
from taniclaw.core.tools import ToolExecutor
from taniclaw.core.memory import Memory
from taniclaw.core.weather import WeatherService
from taniclaw.core.notification import NotificationService
from taniclaw.core.llm import LLMGateway

logger = logging.getLogger("taniclaw.core")


class TaniClawAgent:
    """Main agent orchestrator.

    Runs the core execution loop for all active plants.
    Rules-first, LLM-optional, security-validated.
    """

    def __init__(self, settings: Settings, session_factory):
        self.settings = settings
        self.memory = Memory(session_factory)
        self.knowledge = KnowledgeBase()
        self.state_engine = StateEngine(self.knowledge)
        self.rules_engine = RulesEngine()
        self.security = SecurityGuard(settings)
        self.notification = NotificationService(settings)
        self.tools = ToolExecutor(self.memory, self.notification)
        self.weather_service = WeatherService(settings, self.memory)
        self.llm = LLMGateway(settings) if settings.llm_enabled else None
        logger.info("TaniClaw Agent initialized")

    async def run_cycle(self) -> list[dict]:
        """Execute one full agent cycle for all active plants.

        For each active plant:
        1. Load plant state from memory
        2. Check for state transitions (State Engine)
        3. Fetch weather data
        4. Build context dict
        5. Run Rules Engine with context
        6. IF rules produce actions → validate & execute
        7. ELSE IF LLM enabled → get LLM suggestion → validate & execute
        8. ELSE → log "no action needed"
        9. Store results in memory
        10. Return summary of all actions
        """
        plants = self.memory.get_active_plants()
        if not plants:
            logger.info("No active plants — skipping cycle")
            return []

        all_results = []
        for plant in plants:
            try:
                results = await self.run_single_plant(plant.id)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Cycle failed for plant {plant.id}: {e}", exc_info=True)

        logger.info(f"Cycle complete: {len(all_results)} actions across {len(plants)} plants")
        return all_results

    async def run_single_plant(self, plant_id: uuid.UUID) -> list[dict]:
        """Run cycle for a single plant."""
        plant = self.memory.get_plant(plant_id)
        if not plant or not plant.is_active:
            return []

        results = []

        # 1. Check for state transitions
        new_state = self.state_engine.should_transition(plant)
        if new_state:
            self.memory.update_plant_state(plant_id, new_state.value)
            self.memory.add_history(plant_id, "state_change", {
                "from_state": plant.current_state,
                "to_state": new_state.value,
                "days_in_previous_state": self.state_engine.get_days_in_current_state(plant),
            })
            logger.info(f"Plant {plant.name} transitioned: {plant.current_state} → {new_state.value}")
            # Reload plant after state change
            plant = self.memory.get_plant(plant_id)

        # 2. Fetch weather data
        weather = await self.weather_service.get_weather(plant.latitude, plant.longitude)

        # 3. Build context
        context = self._build_context(plant, weather)

        # 4. Run Rules Engine
        actions = self.rules_engine.evaluate(context)

        # 5. Get stage instructions from knowledge
        stage_instructions = self.knowledge.get_stage_instructions(plant.plant_type, plant.current_state)

        if actions:
            # 6. Execute rule-based actions
            for action in actions:
                action["source"] = "rules"
                is_valid, reason = self.security.validate_action(action, context, self.memory, plant_id)
                if is_valid:
                    result = self.tools.execute(plant_id, action)
                    result["plant_id"] = str(plant_id)
                    result["plant_name"] = plant.name
                    result["rule_id"] = action.get("rule_id")
                    results.append(result)

                    # Send notification for alerts and notifies
                    if action.get("type") in ("alert", "notify") and self.settings.notification_enabled:
                        await self.notification.send(action.get("description", ""), priority="high" if action.get("type") == "alert" else "normal")
                else:
                    logger.info(f"Action blocked by security: {reason}")

        elif self.llm and self.settings.llm_enabled:
            # 7. LLM fallback for complex/unrecognized situations
            logger.info(f"No rules matched for {plant.name} — consulting LLM")
            suggestion = self.llm.suggest_action(context)
            if suggestion:
                suggestion["source"] = "llm"
                is_valid, reason = self.security.validate_action(suggestion, context, self.memory, plant_id)
                if is_valid:
                    result = self.tools.execute(plant_id, suggestion)
                    result["plant_id"] = str(plant_id)
                    result["plant_name"] = plant.name
                    result["source"] = "llm"
                    results.append(result)
                else:
                    logger.warning(f"LLM suggestion blocked by security: {reason}")
        else:
            # 8. No action needed
            self.memory.add_history(plant_id, "cycle", {"message": "No action needed", "context": context})

        return results

    def _build_context(self, plant, weather: dict) -> dict:
        """Build context dict for rules evaluation."""
        days_since_planting = self.state_engine.get_days_since_planting(plant)
        days_in_state = self.state_engine.get_days_in_current_state(plant)
        days_since_water = self.memory.get_days_since_last_action(plant.id, "water")
        days_since_fertilize = self.memory.get_days_since_last_action(plant.id, "fertilize")

        return {
            "plant_id": str(plant.id),
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "plant_state": plant.current_state,
            "days_since_planting": days_since_planting,
            "days_in_state": days_in_state,
            "days_since_last_water": days_since_water,
            "days_since_last_fertilize": days_since_fertilize,
            "today_rainfall_mm": weather.get("rainfall_mm", 0.0),
            "temp_max": weather.get("temp_max", 28.0),
            "temp_min": weather.get("temp_min", 22.0),
            "humidity": weather.get("humidity", 70.0),
            "weather_summary": weather.get("forecast_summary", ""),
            "growing_method": plant.growing_method or "soil",
            "soil_condition": plant.soil_condition or "loamy",
        }

    async def get_daily_instructions(self, plant_id: uuid.UUID) -> dict:
        """Get today's instructions for a plant (for chat interface and API).

        Returns structured instruction set with context.
        """
        plant = self.memory.get_plant(plant_id)
        if not plant:
            return {"error": "Plant not found"}

        weather = await self.weather_service.get_weather(plant.latitude, plant.longitude)
        context = self._build_context(plant, weather)
        actions = self.rules_engine.evaluate(context)
        stage_instructions = self.knowledge.get_stage_instructions(plant.plant_type, plant.current_state)
        harvest_info = self.knowledge.get_harvest_info(plant.plant_type)
        disease_info = self.knowledge.get_disease_info(plant.plant_type)

        instructions = []
        alerts = []
        for action in actions:
            if action.get("type") == "alert":
                alerts.append(action.get("description", ""))
            else:
                instructions.append(action.get("description", ""))

        # Add stage instructions from knowledge base
        instructions.extend(stage_instructions[:3])  # Top 3 stage instructions

        return {
            "plant_id": str(plant_id),
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "plant_state": plant.current_state,
            "days_since_planting": context["days_since_planting"],
            "days_in_state": context["days_in_state"],
            "instructions": instructions,
            "alerts": alerts,
            "weather_summary": weather.get("forecast_summary", ""),
            "weather": {
                "temp_max": weather.get("temp_max"),
                "temp_min": weather.get("temp_min"),
                "humidity": weather.get("humidity"),
                "rainfall_mm": weather.get("rainfall_mm"),
            },
            "harvest_info": harvest_info,
            "common_diseases": [d["name"] for d in disease_info[:3]],
            "next_state": self.state_engine.get_next_state(plant).value if self.state_engine.get_next_state(plant) else None,
        }

    async def chat(self, message: str, plant_id: uuid.UUID | None = None) -> str:
        """Handle chat message from user.

        Knowledge-base first, LLM fallback if enabled.
        """
        message_lower = message.lower()
        plant = self.memory.get_plant(plant_id) if plant_id else None

        context = {}
        if plant:
            weather = await self.weather_service.get_weather(plant.latitude, plant.longitude)
            context = self._build_context(plant, weather)

        # Pattern matching for common queries (no LLM needed)
        if any(kw in message_lower for kw in ["hari ini", "today", "lakukan", "do today"]):
            if plant:
                daily = await self.get_daily_instructions(plant_id)
                instrs = daily.get("instructions", [])
                alerts = daily.get("alerts", [])
                if alerts:
                    response = f"⚠️ PERINGATAN: {alerts[0]}\n\n"
                else:
                    response = ""
                if instrs:
                    response += f"Instruksi hari ini untuk {plant.name}:\n" + "\n".join(f"• {i}" for i in instrs[:5])
                else:
                    response = f"Tidak ada tindakan khusus diperlukan untuk {plant.name} hari ini. Lanjutkan perawatan rutin."
                return response
            return "Pilih tanaman terlebih dahulu untuk melihat instruksi hari ini."

        if any(kw in message_lower for kw in ["status", "kondisi", "bagaimana"]):
            if plant:
                daily = await self.get_daily_instructions(plant_id)
                return (
                    f"🌱 {plant.name} ({plant.plant_type})\n"
                    f"Tahap: {plant.current_state} (hari ke-{daily['days_since_planting']})\n"
                    f"Cuaca: {daily['weather_summary']}"
                )

        if any(kw in message_lower for kw in ["panen", "harvest"]):
            if plant:
                harvest_info = self.knowledge.get_harvest_info(plant.plant_type)
                indicators = harvest_info.get("indicators", [])
                notes = harvest_info.get("notes", "")
                response = f"Tanda-tanda panen {plant.plant_type}:\n"
                response += "\n".join(f"• {i}" for i in indicators[:3])
                if notes:
                    response += f"\n\n{notes}"
                return response

        if any(kw in message_lower for kw in ["siram", "water", "penyiraman"]):
            if plant:
                watering = self.knowledge.get_watering_info(plant.plant_type, plant.current_state)
                if watering:
                    freq = watering.get("frequency_days", 1)
                    amount = watering.get("amount_ml", 200)
                    return f"Jadwal penyiraman {plant.plant_type} saat tahap {plant.current_state}: setiap {freq} hari, {amount}ml per sesi. Siram di pagi hari di pangkal tanaman."

        if any(kw in message_lower for kw in ["pupuk", "fertilize", "fertilizer"]):
            if plant:
                fert = self.knowledge.get_fertilizer_schedule(plant.plant_type, plant.current_state)
                if fert:
                    f = fert[0]
                    return f"Pupuk untuk {plant.plant_type} tahap {plant.current_state}: {f.get('type', 'NPK')}, {f.get('amount_grams', 5)}g setiap {f.get('frequency_days', 14)} hari."

        if any(kw in message_lower for kw in ["hama", "penyakit", "disease", "pest"]):
            if plant:
                diseases = self.knowledge.get_disease_info(plant.plant_type)
                if diseases:
                    d = diseases[0]
                    return f"Penyakit umum {plant.plant_type}: {d['name']}\nGejala: {', '.join(d.get('symptoms', [])[:2])}\nPencegahan: {', '.join(d.get('prevention', [])[:2])}"

        # LLM fallback for unknown queries
        if self.llm and self.settings.llm_enabled:
            return self.llm.chat(message, context)

        return "Saya bisa menjawab pertanyaan tentang: apa yang harus dilakukan hari ini, status tanaman, jadwal panen, cara penyiraman, jadwal pemupukan, dan hama/penyakit. Coba tanyakan salah satunya!"
