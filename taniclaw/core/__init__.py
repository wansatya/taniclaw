"""TaniClaw Core Package."""

import logging
import os
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for TaniClaw."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    # Silence noisy third-party loggers
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("taniclaw")
