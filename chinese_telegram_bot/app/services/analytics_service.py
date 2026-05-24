from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card, Review, User
from app.models.schemas import AnalyticsSummary
from app.repositories.cards import CardRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.statistics import StatisticsRepository
from app.utils.text import pct


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cards = CardRepository(session)
        self.reviews = ReviewRepository(session)
        self.stats = StatisticsRepository(session)

    async def summary(self, user_id: int) -> AnalyticsSummary:
        total_cards = await self.cards.count_for_user(user_id)
        learned_cards = await self.cards.count_learned(user_id)
        due_cards = len(await self.cards.get_due_cards(user_id, limit=1000))
        user_row = await self.session.execute(select(User).where(User.telegram_id == user_id))
        user = user_row.scalar_one_or_none()

        accuracy = await self.reviews.accuracy(user_id)
        retention = await self.reviews.retention(user_id)
        weak_cards = await self.cards.get_weak_cards(user_id, limit=10)
        hsk_progress = await self.cards.get_hsk_progress(user_id)
        monthly_progress = await self.stats.monthly_progress(user_id, days=30)
        recent = await self.reviews.recent_by_day(user_id, limit=30)

        study_time = (user.total_study_seconds if user else 0) / 60
        streak = user.streak if user else 0
        cards_per_day = round(learned_cards / max(1, len(monthly_progress)), 2)

        weak_words = [
            {
                "hanzi": card.hanzi,
                "translation": card.translation,
                "lapses": card.lapses,
                "ease_factor": card.ease_factor,
                "due_at": card.due_at.isoformat(),
            }
            for card in weak_cards
        ]

        review_forecast = [
            {"day": day, "reviews": count}
            for day, count in recent
        ]

        return AnalyticsSummary(
            total_cards=total_cards,
            learned_cards=learned_cards,
            due_cards=due_cards,
            streak=streak,
            retention_rate=retention,
            accuracy=accuracy,
            weak_words=weak_words,
            hsk_progress=hsk_progress,
            study_time_minutes=round(study_time, 1),
            cards_per_day=cards_per_day,
            monthly_progress=monthly_progress,
            review_forecast=review_forecast,
            learning_speed=round(learned_cards / max(1, study_time / 60), 2) if study_time else 0.0,
        )
