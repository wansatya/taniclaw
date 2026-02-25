"""TaniClaw Weather Service — fetches from Open-Meteo API with caching."""

import logging
from datetime import date, datetime, timezone

import httpx

from taniclaw.core.config import Settings

logger = logging.getLogger("taniclaw.weather")

OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"


class WeatherService:
    """Fetches weather data from Open-Meteo API (free, no API key required).

    Caches results in database to minimize API calls.
    Falls back to safe defaults if API is unreachable.
    """

    def __init__(self, settings: Settings, memory):
        self.settings = settings
        self.memory = memory
        self.base_url = settings.weather_api_base

    async def get_weather(self, lat: float, lon: float, for_date: date | None = None) -> dict:
        """Get weather for a location. Check cache first.

        Returns a dict with temp_max, temp_min, humidity, rainfall_mm, forecast_summary.
        """
        if for_date is None:
            for_date = date.today()

        # Round coordinates to 2 decimal places for cache key consistency
        lat_r = round(lat, 2)
        lon_r = round(lon, 2)

        # Try cache first
        cached = self.memory.get_cached_weather(lat_r, lon_r, for_date)
        if cached:
            logger.debug(f"Weather cache hit for ({lat_r}, {lon_r}) on {for_date}")
            return self._format_from_cache(cached)

        # Fetch from API
        try:
            data = await self.fetch_from_api(lat_r, lon_r)
            weather = self._parse_response(data, for_date)
            # Store in cache
            self.memory.cache_weather({
                "latitude": lat_r,
                "longitude": lon_r,
                "date": for_date,
                "temp_max": weather.get("temp_max"),
                "temp_min": weather.get("temp_min"),
                "humidity": weather.get("humidity"),
                "rainfall": weather.get("rainfall_mm"),
                "raw_data": data,
            })
            return weather
        except Exception as e:
            logger.warning(f"Weather API failed for ({lat}, {lon}): {e}. Using safe defaults.")
            return self._safe_defaults()

    async def fetch_from_api(self, lat: float, lon: float) -> dict:
        """Call Open-Meteo API and return raw response."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "relative_humidity_2m_max",
            ],
            "timezone": "auto",
            "forecast_days": 3,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPEN_METEO_ENDPOINT, params=params)
            response.raise_for_status()
            return response.json()

    def _parse_response(self, data: dict, for_date: date) -> dict:
        """Parse Open-Meteo response for a specific date."""
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        date_str = for_date.isoformat()

        idx = 0  # Default to today
        if date_str in dates:
            idx = dates.index(date_str)

        temp_max_list = daily.get("temperature_2m_max", [None])
        temp_min_list = daily.get("temperature_2m_min", [None])
        precip_list = daily.get("precipitation_sum", [0])
        humidity_list = daily.get("relative_humidity_2m_max", [70])

        temp_max = temp_max_list[idx] if idx < len(temp_max_list) else 28.0
        temp_min = temp_min_list[idx] if idx < len(temp_min_list) else 22.0
        rainfall = precip_list[idx] if idx < len(precip_list) else 0.0
        humidity = humidity_list[idx] if idx < len(humidity_list) else 70.0

        # Build forecast summary
        if rainfall and rainfall >= 50:
            summary = "Hujan lebat diprediksi hari ini. Pastikan drainase baik."
        elif rainfall and rainfall >= 10:
            summary = f"Hujan sedang diprediksi ({rainfall:.0f}mm). Lewati penyiraman."
        elif temp_max and temp_max >= 38:
            summary = f"Gelombang panas! Suhu maks {temp_max:.0f}°C. Beri naungan dan siram ekstra."
        elif temp_max and temp_max >= 35:
            summary = f"Hari panas ({temp_max:.0f}°C). Pertimbangkan penyiraman ekstra sore hari."
        else:
            summary = f"Cuaca normal. Suhu {temp_min:.0f}-{temp_max:.0f}°C, kelembaban {humidity:.0f}%."

        return {
            "temp_max": temp_max or 28.0,
            "temp_min": temp_min or 22.0,
            "humidity": humidity or 70.0,
            "rainfall_mm": rainfall or 0.0,
            "forecast_summary": summary,
        }

    def _format_from_cache(self, cache) -> dict:
        """Format WeatherCache object to standard dict."""
        temp_max = cache.temp_max or 28.0
        temp_min = cache.temp_min or 22.0
        humidity = cache.humidity or 70.0
        rainfall = cache.rainfall or 0.0

        if rainfall >= 50:
            summary = f"Hujan lebat ({rainfall:.0f}mm). Data dari cache."
        elif rainfall >= 10:
            summary = f"Hujan sedang ({rainfall:.0f}mm). Data dari cache."
        else:
            summary = f"Cuaca normal. {temp_min:.0f}-{temp_max:.0f}°C. Data dari cache."

        return {
            "temp_max": temp_max,
            "temp_min": temp_min,
            "humidity": humidity,
            "rainfall_mm": rainfall,
            "forecast_summary": summary,
        }

    def _safe_defaults(self) -> dict:
        """Return safe default weather values when API is unavailable."""
        return {
            "temp_max": 28.0,
            "temp_min": 22.0,
            "humidity": 70.0,
            "rainfall_mm": 0.0,
            "forecast_summary": "Data cuaca tidak tersedia. Gunakan penilaian lokal Anda.",
        }
