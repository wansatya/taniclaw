"""TaniClaw CLI — main entry point for `taniclaw start`."""

import sys
import os


def main():
    """Start TaniClaw server."""
    import uvicorn
    from taniclaw.core.config import get_settings

    settings = get_settings()

    print("🌱 TaniClaw v1 — Lightweight Autonomous Agriculture Skill")
    print(f"   Starting on http://{settings.host}:{settings.port}")
    print(f"   Dashboard: http://{settings.host}:{settings.port}/")
    print(f"   Chat:      http://{settings.host}:{settings.port}/chat")
    print(f"   API Docs:  http://{settings.host}:{settings.port}/docs")
    print("")

    uvicorn.run(
        "taniclaw.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
