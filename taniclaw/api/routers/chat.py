"""Chat router — conversational interface."""

from fastapi import APIRouter, Depends
from taniclaw.api.deps import get_agent
from taniclaw.api.schemas import ChatRequest, ChatResponse
from taniclaw.core.core import TaniClawAgent

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    agent: TaniClawAgent = Depends(get_agent),
):
    """Chat with TaniClaw.

    Supported queries:
    - "Apa yang harus saya lakukan hari ini?"
    - "Bagaimana kondisi tanaman saya?"
    - "Kapan bisa dipanen?"
    - "Cara menyiram?"
    - "Jadwal pupuk?"
    - "Hama dan penyakit apa yang perlu diwaspadai?"
    """
    reply = await agent.chat(body.message, plant_id=body.plant_id)
    return ChatResponse(reply=reply, actions=[])
