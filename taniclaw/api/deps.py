"""TaniClaw API — dependency injection."""

from typing import Annotated
from fastapi import Depends, Request
from taniclaw.core.core import TaniClawAgent


def get_agent(request: Request) -> TaniClawAgent:
    """Get TaniClaw agent from app state."""
    return request.app.state.agent
