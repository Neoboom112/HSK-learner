from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import get_settings
from app.database.models import ScheduledReview, User
from app.database.session import async_session
from app.i18n import get_localizer
from app.repositories.cards import CardRepository
from app.utils.text import compact_dt

logger = logging.getLogger(__name__)


class ReviewScheduler:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.settings = get_settings()

    async def start(self) -> None:
        self.scheduler.add_job(self._tick, "interval", seconds=self.settings.review_check_seconds, max_instances=1)
        self.scheduler.start()
        logger.info("Review scheduler started")

    async def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Review scheduler stopped")

    async def _tick(self) -> None:
        async with async_session() as session:
            users = await session.execute(select(User).where(User.telegram_id != 0))
            user_rows = users.scalars().all()
            repo = CardRepository(session)
            for user in user_rows:
                due_cards = await repo.get_due_cards(user.id, limit=self.settings.daily_review_limit)
                if not due_cards:
                    continue
                recent = await session.execute(
                    select(ScheduledReview).where(
                        ScheduledReview.user_id == user.id,
                        ScheduledReview.status == "notified",
                        ScheduledReview.notified_at >= datetime.now(timezone.utc) - timedelta(minutes=30),
                    )
                )
                if recent.scalars().first():
                    continue
                for card in due_cards[:10]:
                    session.add(
                        ScheduledReview(
                            user_id=user.id,
                            card_id=card.id,
                            due_at=card.due_at,
                            notified_at=datetime.now(timezone.utc),
                            status="notified",
                            metadata={"mode": "reminder"},
                        )
                    )
                await session.flush()
                t = get_localizer(user.language).t
                text = (
                    f"⏰ {t('progress_title')}\n"
                    f"{len(due_cards)} due cards.\n"
                    f"Last due: {compact_dt(due_cards[0].due_at)}"
                )
                try:
                    await self.bot.send_message(user.telegram_id, text)
                except Exception:
                    logger.exception("Failed to send review reminder to %s", user.telegram_id)
            await session.commit()
