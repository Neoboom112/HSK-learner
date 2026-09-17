from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Review, Statistic


class StatisticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_daily(
        self,
        user_id: int,
        stat_date: datetime,
        cards_learned: int = 0,
        reviews_done: int = 0,
        correct_answers: int = 0,
        study_seconds: int = 0,
        extra: dict | None = None,
    ) -> None:
        result = await self.session.execute(
            select(Statistic).where(Statistic.user_id == user_id, func.date(Statistic.stat_date) == stat_date.date())
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = Statistic(
                user_id=user_id,
                stat_date=stat_date,
                cards_learned=cards_learned,
                reviews_done=reviews_done,
                correct_answers=correct_answers,
                study_seconds=study_seconds,
                extra=extra or {},
            )
            self.session.add(row)
        else:
            row.cards_learned += cards_learned
            row.reviews_done += reviews_done
            row.correct_answers += correct_answers
            row.study_seconds += study_seconds
            if extra:
                row.extra = {**row.extra, **extra}
        await self.session.flush()

    async def monthly_progress(self, user_id: int, days: int = 30) -> list[dict[str, int]]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = await self.session.execute(
            select(func.date(Review.reviewed_at), func.count(Review.id))
            .where(Review.user_id == user_id, Review.reviewed_at >= since)
            .group_by(func.date(Review.reviewed_at))
            .order_by(func.date(Review.reviewed_at))
        )
        return [{"date": str(day), "reviews": int(count)} for day, count in rows.all()]

    async def delete_for_user(self, user_id: int) -> int:
        """Remove the daily rollups of a user."""
        result = await self.session.execute(delete(Statistic).where(Statistic.user_id == user_id))
        await self.session.flush()
        return int(result.rowcount or 0)
