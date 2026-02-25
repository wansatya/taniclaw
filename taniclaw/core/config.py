"""TaniClaw configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://taniclaw:taniclaw@localhost:5432/taniclaw"

    # Scheduler
    scheduler_interval_minutes: int = 60

    # Weather
    weather_api_base: str = "https://api.open-meteo.com/v1"

    # LLM (optional) — using Groq SDK directly
    llm_enabled: bool = False
    llm_model: str = "llama-3.1-8b-instant"
    groq_api_key: str = ""
    llm_fallback_model: str = "llama-3.3-70b-versatile"

    # Security
    max_watering_amount_ml: int = 500
    max_daily_actions: int = 50
    max_fertilizer_grams: int = 20

    # Notification
    notification_enabled: bool = False
    whatsapp_api_url: str = ""
    whatsapp_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # General
    timezone: str = "Asia/Jakarta"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_prefix": "TANICLAW_",
        "extra": "ignore",
    }


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
