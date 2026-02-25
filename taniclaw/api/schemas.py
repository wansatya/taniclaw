"""TaniClaw API — Pydantic request/response schemas."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Plant schemas ─────────────────────────────────────────────────────────────

class PlantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="User-given plant name")
    plant_type: str = Field(..., description="chili, tomato, spinach, lettuce, hydroponic")
    location: str = Field(..., description="Location description, e.g. 'Jakarta, Indonesia'")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    plant_date: date
    growing_method: str | None = Field(None, description="soil, hydroponic, pot")
    soil_condition: str | None = Field(None, description="clay, sandy, loamy")
    notes: str | None = None


class PlantUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    growing_method: str | None = None
    soil_condition: str | None = None
    notes: str | None = None
    current_state: str | None = None


class PlantResponse(BaseModel):
    id: uuid.UUID
    name: str
    plant_type: str
    location: str
    latitude: float
    longitude: float
    current_state: str
    plant_date: date
    days_since_planting: int
    days_in_state: int
    growing_method: str | None
    soil_condition: str | None
    notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Action schemas ────────────────────────────────────────────────────────────

class ActionResponse(BaseModel):
    id: uuid.UUID
    plant_id: uuid.UUID
    action_type: str
    description: str
    source: str
    status: str
    executed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OverrideRequest(BaseModel):
    action_type: str = Field(..., description="water, fertilize, harvest, notify, alert, log")
    description: str
    amount_ml: int | None = None
    amount_grams: int | None = None


# ── Chat schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    plant_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    reply: str
    actions: list[ActionResponse] = []


# ── Daily instruction schemas ─────────────────────────────────────────────────

class WeatherData(BaseModel):
    temp_max: float | None
    temp_min: float | None
    humidity: float | None
    rainfall_mm: float | None
    forecast_summary: str


class DailyInstructionResponse(BaseModel):
    plant_id: uuid.UUID
    plant_name: str
    plant_type: str
    plant_state: str
    days_since_planting: int
    days_in_state: int
    instructions: list[str]
    alerts: list[str]
    weather_summary: str | None
    weather: WeatherData | None
    harvest_info: dict[str, Any]
    common_diseases: list[str]
    next_state: str | None


# ── Farm schemas ──────────────────────────────────────────────────────────────

class PlantSummary(BaseModel):
    id: uuid.UUID
    name: str
    plant_type: str
    current_state: str
    days_since_planting: int


class FarmStatus(BaseModel):
    total_plants: int
    active_plants: int
    plants: list[PlantSummary]


class HistoryResponse(BaseModel):
    id: uuid.UUID
    plant_id: uuid.UUID
    event_type: str
    event_data: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class DailySummary(BaseModel):
    date: date
    total_actions: int
    plants_count: int
    action_breakdown: dict[str, int]
    alerts: list[str]
    instructions: list[str]


# ── Generic response ──────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    status: str
    message: str | None = None
