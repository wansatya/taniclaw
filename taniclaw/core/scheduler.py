"""TaniClaw Scheduler — APScheduler-based cron loop."""

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from taniclaw.core.config import Settings

logger = logging.getLogger("taniclaw.scheduler")


class TaniClawScheduler:
    """Runs the agent loop on a cron schedule.

    Default interval: 1 hour (configurable).
    No LLM required for scheduling.
    """

    def __init__(self, agent, settings: Settings):
        self.agent = agent
        self.settings = settings
        self.scheduler = BackgroundScheduler(timezone=settings.timezone)
        self._loop: asyncio.AbstractEventLoop | None = None

    def _run_async_cycle(self):
        """Run async agent cycle from sync APScheduler context."""
        try:
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(self.agent.run_cycle(), self._loop)
            else:
                asyncio.run(self.agent.run_cycle())
        except Exception as e:
            logger.error(f"Scheduled cycle failed: {e}", exc_info=True)

    def start(self, loop: asyncio.AbstractEventLoop | None = None):
        """Start the scheduler with configured interval."""
        self._loop = loop
        self.scheduler.add_job(
            self._run_async_cycle,
            "interval",
            minutes=self.settings.scheduler_interval_minutes,
            id="taniclaw_main_loop",
            name="TaniClaw Main Loop",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(f"Scheduler started — interval: {self.settings.scheduler_interval_minutes} minutes")

    def stop(self):
        """Gracefully stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def trigger_now(self):
        """Manually trigger a cycle from sync context."""
        self._run_async_cycle()
