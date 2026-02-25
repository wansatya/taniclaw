"""Farm router — overall farm status and history."""

from datetime import date

from fastapi import APIRouter, Depends

from taniclaw.api.deps import get_agent
from taniclaw.api.schemas import (
    DailySummary,
    FarmStatus,
    HistoryResponse,
    PlantSummary,
)
from taniclaw.core.core import TaniClawAgent

router = APIRouter()


@router.get("/status", response_model=FarmStatus)
async def get_farm_status(
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get overall farm status."""
    all_plants = agent.memory.get_all_plants()
    active_plants = [p for p in all_plants if p.is_active]
    return FarmStatus(
        total_plants=len(all_plants),
        active_plants=len(active_plants),
        plants=[
            PlantSummary(
                id=p.id,
                name=p.name,
                plant_type=p.plant_type,
                current_state=p.current_state,
                days_since_planting=agent.state_engine.get_days_since_planting(p),
            )
            for p in active_plants
        ],
    )


@router.get("/history", response_model=list[HistoryResponse])
async def get_farm_history(
    limit: int = 100,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get farm history (all events across all plants)."""
    history = agent.memory.get_all_history(limit=limit)
    return [
        HistoryResponse(
            id=h.id,
            plant_id=h.plant_id,
            event_type=h.event_type,
            event_data=h.event_data,
            created_at=h.created_at,
        )
        for h in history
    ]


@router.get("/summary", response_model=DailySummary)
async def get_daily_summary(
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get daily summary across all plants."""
    active_plants = agent.memory.get_active_plants()
    today = date.today()

    all_instructions = []
    all_alerts = []
    action_breakdown: dict[str, int] = {}
    total_actions = 0

    for plant in active_plants:
        try:
            daily = await agent.get_daily_instructions(plant.id)
            instrs = daily.get("instructions", [])
            alerts = daily.get("alerts", [])
            all_instructions.extend(instrs[:2])
            all_alerts.extend(alerts)
        except Exception:
            pass

        today_actions = agent.memory.get_today_actions(plant.id)
        total_actions += len(today_actions)
        for a in today_actions:
            action_breakdown[a.action_type] = action_breakdown.get(a.action_type, 0) + 1

    return DailySummary(
        date=today,
        total_actions=total_actions,
        plants_count=len(active_plants),
        action_breakdown=action_breakdown,
        alerts=all_alerts[:5],
        instructions=all_instructions[:10],
    )
