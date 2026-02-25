"""Weather router — weather data for plant locations."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from taniclaw.api.deps import get_agent
from taniclaw.api.schemas import WeatherData
from taniclaw.core.core import TaniClawAgent

router = APIRouter()


@router.get("/{plant_id}", response_model=WeatherData)
async def get_plant_weather(
    plant_id: uuid.UUID,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get current weather forecast for a plant's location."""
    plant = agent.memory.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    weather = await agent.weather_service.get_weather(plant.latitude, plant.longitude)
    return WeatherData(
        temp_max=weather.get("temp_max"),
        temp_min=weather.get("temp_min"),
        humidity=weather.get("humidity"),
        rainfall_mm=weather.get("rainfall_mm"),
        forecast_summary=weather.get("forecast_summary", ""),
    )
