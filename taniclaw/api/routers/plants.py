"""Plants router — CRUD endpoints."""

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from taniclaw.api.deps import get_agent
from taniclaw.api.schemas import (
    DailyInstructionResponse,
    PlantCreate,
    PlantResponse,
    PlantUpdate,
    StatusResponse,
    WeatherData,
)
from taniclaw.core.core import TaniClawAgent
from taniclaw.core.state import StateEngine, PlantState

router = APIRouter()


def _plant_response(plant, agent: TaniClawAgent) -> PlantResponse:
    """Convert Plant model to PlantResponse schema."""
    state_engine = agent.state_engine
    days_since_planting = state_engine.get_days_since_planting(plant)
    days_in_state = state_engine.get_days_in_current_state(plant)
    return PlantResponse(
        id=plant.id,
        name=plant.name,
        plant_type=plant.plant_type,
        location=plant.location,
        latitude=plant.latitude,
        longitude=plant.longitude,
        current_state=plant.current_state,
        plant_date=plant.plant_date,
        days_since_planting=days_since_planting,
        days_in_state=days_in_state,
        growing_method=plant.growing_method,
        soil_condition=plant.soil_condition,
        notes=plant.notes,
        is_active=plant.is_active,
        created_at=plant.created_at,
    )


@router.post("", response_model=PlantResponse, status_code=201)
async def create_plant(
    body: PlantCreate,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Register a new plant."""
    # Validate plant type
    supported = agent.knowledge.get_supported_plants()
    if body.plant_type not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported plant type '{body.plant_type}'. Supported: {supported}",
        )
    plant = agent.memory.create_plant({
        "name": body.name,
        "plant_type": body.plant_type,
        "location": body.location,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "plant_date": body.plant_date,
        "growing_method": body.growing_method,
        "soil_condition": body.soil_condition,
        "notes": body.notes,
        "current_state": "seed",
        "state_changed_at": datetime.now(timezone.utc),
    })
    agent.memory.add_history(plant.id, "created", {
        "plant_type": body.plant_type,
        "location": body.location,
        "plant_date": body.plant_date.isoformat(),
    })
    return _plant_response(plant, agent)


@router.get("", response_model=list[PlantResponse])
async def list_plants(
    active_only: bool = True,
    agent: TaniClawAgent = Depends(get_agent),
):
    """List all plants."""
    if active_only:
        plants = agent.memory.get_active_plants()
    else:
        plants = agent.memory.get_all_plants()
    return [_plant_response(p, agent) for p in plants]


@router.get("/{plant_id}", response_model=PlantResponse)
async def get_plant(
    plant_id: uuid.UUID,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get plant details."""
    plant = agent.memory.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    return _plant_response(plant, agent)


@router.put("/{plant_id}", response_model=PlantResponse)
async def update_plant(
    plant_id: uuid.UUID,
    body: PlantUpdate,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Update plant details."""
    update_data = body.model_dump(exclude_none=True)
    if "current_state" in update_data:
        # Validate state
        try:
            PlantState(update_data["current_state"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {update_data['current_state']}")
        update_data["state_changed_at"] = datetime.now(timezone.utc)

    plant = agent.memory.update_plant(plant_id, update_data)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    return _plant_response(plant, agent)


@router.delete("/{plant_id}", response_model=StatusResponse)
async def deactivate_plant(
    plant_id: uuid.UUID,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Deactivate (soft-delete) a plant."""
    ok = agent.memory.deactivate_plant(plant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Plant not found")
    return StatusResponse(status="ok", message="Plant deactivated")


@router.get("/{plant_id}/instructions", response_model=DailyInstructionResponse)
async def get_plant_instructions(
    plant_id: uuid.UUID,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get today's instructions for a plant."""
    plant = agent.memory.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    daily = await agent.get_daily_instructions(plant_id)
    if "error" in daily:
        raise HTTPException(status_code=404, detail=daily["error"])

    weather = daily.get("weather") or {}
    return DailyInstructionResponse(
        plant_id=plant_id,
        plant_name=daily["plant_name"],
        plant_type=daily["plant_type"],
        plant_state=daily["plant_state"],
        days_since_planting=daily["days_since_planting"],
        days_in_state=daily["days_in_state"],
        instructions=daily.get("instructions", []),
        alerts=daily.get("alerts", []),
        weather_summary=daily.get("weather_summary"),
        weather=WeatherData(
            temp_max=weather.get("temp_max"),
            temp_min=weather.get("temp_min"),
            humidity=weather.get("humidity"),
            rainfall_mm=weather.get("rainfall_mm"),
            forecast_summary=daily.get("weather_summary", ""),
        ),
        harvest_info=daily.get("harvest_info", {}),
        common_diseases=daily.get("common_diseases", []),
        next_state=daily.get("next_state"),
    )
