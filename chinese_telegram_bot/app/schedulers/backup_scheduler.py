from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.services.backup_service import BackupService

logger = logging.getLogger(__name__)


class BackupScheduler:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.settings = get_settings()

    async def start(self) -> None:
        self.scheduler.add_job(self._tick, "interval", hours=self.settings.backup_interval_hours, max_instances=1)
        self.scheduler.start()
        logger.info("Backup scheduler started")

    async def stop(self) -> None:
        if not self.scheduler.running:
            return
        self.scheduler.shutdown(wait=False)
        # AsyncIOScheduler finishes shutting down on the next loop iteration.
        for _ in range(20):
            if not self.scheduler.running:
                break
            await asyncio.sleep(0.05)
        logger.info("Backup scheduler stopped")

    async def _tick(self) -> None:
        try:
            backup_path = BackupService().run_backup()
            logger.info("Backup created: %s", backup_path)
        except Exception:
            logger.exception("Backup job failed")
