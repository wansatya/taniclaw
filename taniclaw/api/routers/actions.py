"""Actions router — action history, triggers, overrides."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from taniclaw.api.deps import get_agent
from taniclaw.api.schemas import ActionResponse, OverrideRequest, StatusResponse
from taniclaw.core.core import TaniClawAgent

router = APIRouter()


def _action_response(action) -> ActionResponse:
    return ActionResponse(
        id=action.id,
        plant_id=action.plant_id,
        action_type=action.action_type,
        description=action.description,
        source=action.source,
        status=action.status,
        executed_at=action.executed_at,
        created_at=action.created_at,
    )


@router.get("/{plant_id}", response_model=list[ActionResponse])
async def get_actions(
    plant_id: uuid.UUID,
    limit: int = 50,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get action history for a plant."""
    plant = agent.memory.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    actions = agent.memory.get_actions(plant_id, limit=limit)
    return [_action_response(a) for a in actions]


@router.get("/{plant_id}/today", response_model=list[ActionResponse])
async def get_today_actions(
    plant_id: uuid.UUID,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Get today's actions for a plant."""
    plant = agent.memory.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    actions = agent.memory.get_today_actions(plant_id)
    return [_action_response(a) for a in actions]


@router.post("/{plant_id}/trigger", response_model=list[ActionResponse])
async def trigger_agent_cycle(
    plant_id: uuid.UUID,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Manually trigger an agent cycle for a specific plant."""
    plant = agent.memory.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    results = await agent.run_single_plant(plant_id)
    # Fetch executed actions from memory
    actions = agent.memory.get_today_actions(plant_id)
    return [_action_response(a) for a in actions[:len(results)]]


@router.post("/{plant_id}/override", response_model=ActionResponse)
async def human_override(
    plant_id: uuid.UUID,
    body: OverrideRequest,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Human override — execute an action manually, always allowed."""
    plant = agent.memory.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    action_dict = {
        "type": body.action_type,
        "description": body.description,
        "source": "manual",
        "amount_ml": body.amount_ml,
        "amount_grams": body.amount_grams,
    }

    is_valid, reason = agent.security.validate_action(action_dict, {}, agent.memory, plant_id)
    if not is_valid and reason != "human_override":
        raise HTTPException(status_code=400, detail=f"Validation failed: {reason}")

    result = agent.tools.execute(plant_id, action_dict)
    actions = agent.memory.get_actions(plant_id, limit=1)
    if not actions:
        raise HTTPException(status_code=500, detail="Action execution failed")
    return _action_response(actions[0])
