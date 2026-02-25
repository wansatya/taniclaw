"""TaniClaw LLM Gateway — optional Groq integration via Groq SDK.

Used ONLY when:
  - No rule exists for the situation
  - Complex reasoning required

Strategy:
  - Small model first (llama-3.1-8b-instant)
  - Large model fallback (llama-3.3-70b-versatile)
  - LLM cannot execute actions — only suggests
  - Security Guard validates all LLM suggestions

Token Optimization:
  - Zero tokens by default (LLM disabled)
  - No chat history sent — single structured prompt
  - JSON output only
  - No autonomous LLM loops
"""

import json
import logging

from taniclaw.core.config import Settings

logger = logging.getLogger("taniclaw.llm")

SYSTEM_PROMPT = """You are TaniClaw, a lightweight autonomous agriculture assistant.

Your role is to help users grow food by providing specific, actionable advice.

RULES:
- Respond with valid JSON only — no markdown, no explanation text outside JSON
- Suggest exactly ONE action per response
- Action types allowed: water, fertilize, harvest, notify, alert, log
- Keep descriptions short and practical (max 150 chars)
- All descriptions must be in Bahasa Indonesia
- You CANNOT execute actions — only suggest

Response format:
{
  "type": "water|fertilize|harvest|notify|alert|log",
  "description": "Instruksi singkat dalam Bahasa Indonesia",
  "amount_ml": 300,
  "amount_grams": null,
  "confidence": 0.8,
  "reasoning": "brief English reason"
}"""


class LLMGateway:
    """Optional LLM integration via Groq SDK.

    Only use when rules engine has no matching rule.
    LLM output is always validated by SecurityGuard before execution.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.llm_enabled
        self._client = None

        if self.enabled:
            if not settings.groq_api_key:
                logger.warning("LLM enabled but TANICLAW_GROQ_API_KEY not set — disabling LLM")
                self.enabled = False
            else:
                try:
                    from groq import Groq
                    self._client = Groq(api_key=settings.groq_api_key)
                    logger.info(f"LLM Gateway initialized with model: {settings.llm_model}")
                except ImportError:
                    logger.warning("groq package not installed — LLM disabled")
                    self.enabled = False

    def suggest_action(self, context: dict) -> dict | None:
        """Ask LLM for a suggested action when rules engine has no match.

        Returns parsed JSON action dict or None.
        Token usage: only when rules engine fails AND LLM is enabled.
        """
        if not self.enabled or not self._client:
            return None

        messages = self._build_prompt(context)

        # Try small model first, then fallback
        for model in [self.settings.llm_model, self.settings.llm_fallback_model]:
            result = self._call_llm(messages, model)
            if result:
                result["source"] = "llm"
                logger.info(f"LLM suggested action: {result.get('type')} (model={model})")
                return result

        return None

    def chat(self, user_message: str, context: dict | None = None) -> str:
        """Handle a free-form chat message from the user.

        Returns a natural language response in Bahasa Indonesia.
        Only called for complex questions when LLM is enabled.
        """
        if not self.enabled or not self._client:
            return "Maaf, fitur chat AI tidak aktif. Silakan aktifkan LLM di konfigurasi."

        system = """Kamu adalah TaniClaw, asisten pertanian yang ramah dan berpengetahuan.
Jawab pertanyaan pengguna tentang tanaman, pertanian, dan berkebun dalam Bahasa Indonesia.
Berikan saran yang praktis, spesifik, dan mudah dipahami.
Jangan terlalu panjang — maksimal 3-4 kalimat per respons."""

        ctx_str = ""
        if context:
            plant_name = context.get("plant_name", "tanaman")
            plant_state = context.get("plant_state", "tidak diketahui")
            plant_type = context.get("plant_type", "tidak diketahui")
            ctx_str = f"\n\nKonteks tanaman: {plant_name} ({plant_type}), tahap: {plant_state}."

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message + ctx_str},
        ]

        for model in [self.settings.llm_model, self.settings.llm_fallback_model]:
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=400,
                    temperature=0.7,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"LLM chat failed with {model}: {e}")
                continue

        return "Maaf, terjadi kesalahan saat menghubungi AI. Coba lagi nanti."

    def _build_prompt(self, context: dict) -> list[dict]:
        """Build minimal structured prompt. No chat history."""
        plant_summary = (
            f"Plant: {context.get('plant_name', 'Unknown')} ({context.get('plant_type', 'unknown')})\n"
            f"State: {context.get('plant_state', 'seed')}\n"
            f"Days since planting: {context.get('days_since_planting', 0)}\n"
            f"Days in current state: {context.get('days_in_state', 0)}\n"
            f"Days since last watering: {context.get('days_since_last_water', 0)}\n"
            f"Days since last fertilizing: {context.get('days_since_last_fertilize', 0)}\n"
            f"Weather — Temp: {context.get('temp_max', 28)}°C max, "
            f"Rainfall: {context.get('today_rainfall_mm', 0)}mm, "
            f"Humidity: {context.get('humidity', 70)}%\n"
            f"Growing method: {context.get('growing_method', 'soil')}"
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"What action should I take for this plant?\n\n{plant_summary}"},
        ]

    def _call_llm(self, messages: list[dict], model: str | None = None) -> dict | None:
        """Call Groq SDK with model fallback. Returns parsed JSON or None."""
        target_model = model or self.settings.llm_model
        try:
            response = self._client.chat.completions.create(
                model=target_model,
                messages=messages,
                max_tokens=300,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"LLM returned invalid JSON with {target_model}: {e}")
            return None
        except Exception as e:
            logger.warning(f"LLM call failed with {target_model}: {e}")
            return None
