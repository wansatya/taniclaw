"""TaniClaw FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from taniclaw.core.config import get_settings
from taniclaw.core.core import TaniClawAgent
from taniclaw.core.scheduler import TaniClawScheduler
from taniclaw.models.base import create_session_factory
from taniclaw.models import Base
from taniclaw.api.routers import plants, actions, chat, farm, weather

logger = logging.getLogger("taniclaw.api")

_FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — startup and shutdown."""
    settings = get_settings()

    # Setup logging
    from taniclaw.core import setup_logging
    setup_logging(settings.log_level)

    # Database
    engine, SessionFactory = create_session_factory(settings.database_url)

    # Create tables (idempotent — skip in production, use Alembic instead)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"DB init failed: {e}")

    # Initialize agent
    agent = TaniClawAgent(settings, SessionFactory)
    app.state.agent = agent

    # Scheduler
    loop = asyncio.get_event_loop()
    scheduler = TaniClawScheduler(agent, settings)
    scheduler.start(loop=loop)
    app.state.scheduler = scheduler

    logger.info(f"TaniClaw v1 started on http://{settings.host}:{settings.port}")
    yield

    # Shutdown
    scheduler.stop()
    engine.dispose()
    logger.info("TaniClaw shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TaniClaw v1",
        description="Lightweight Autonomous Agriculture Skill — Food Security Agent for Everyone",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    app.include_router(plants.router, prefix="/api/plants", tags=["plants"])
    app.include_router(actions.router, prefix="/api/actions", tags=["actions"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(farm.router, prefix="/api/farm", tags=["farm"])
    app.include_router(weather.router, prefix="/api/weather", tags=["weather"])

    # Health check
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": "taniclaw", "version": "1.0.0"}

    @app.get("/api/plants-supported", tags=["system"])
    async def supported_plants(request):
        from taniclaw.core.knowledge import KnowledgeBase
        kb = KnowledgeBase()
        return {"supported": kb.get_supported_plants()}

    # Frontend SPA — serve static files
    if _FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_dashboard():
            return FileResponse(str(_FRONTEND_DIR / "index.html"))

        @app.get("/chat", include_in_schema=False)
        async def serve_chat():
            return FileResponse(str(_FRONTEND_DIR / "chat.html"))

    return app


app = create_app()
