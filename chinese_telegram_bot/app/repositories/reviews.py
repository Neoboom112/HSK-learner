from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Review


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        user_id: int,
        card_id: int,
        grade: int,
        is_correct: bool,
        mode: str,
        response_time_ms: int | None = None,
        metadata: dict | None = None,
    ) -> Review:
        review = Review(
            user_id=user_id,
            card_id=card_id,
            grade=grade,
            is_correct=is_correct,
            mode=mode,
            response_time_ms=response_time_ms,
            reviewed_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        self.session.add(review)
        await self.session.flush()
        return review

    async def accuracy(self, user_id: int) -> float:
        total = await self.session.execute(select(func.count(Review.id)).where(Review.user_id == user_id))
        total_count = int(total.scalar_one())
        if total_count == 0:
            return 0.0
        correct = await self.session.execute(select(func.count(Review.id)).where(Review.user_id == user_id, Review.is_correct.is_(True)))
        return round(int(correct.scalar_one()) * 100 / total_count, 1)

    async def retention(self, user_id: int, days: int = 30) -> float:
        total = await self.session.execute(select(func.count(Review.id)).where(Review.user_id == user_id))
        total_count = int(total.scalar_one())
        if total_count == 0:
            return 0.0
        good = await self.session.execute(
            select(func.count(Review.id)).where(Review.user_id == user_id, Review.grade >= 3)
        )
        return round(int(good.scalar_one()) * 100 / total_count, 1)

    async def recent_by_day(self, user_id: int, limit: int = 30) -> list[tuple[str, int]]:
        rows = await self.session.execute(
            select(func.date(Review.reviewed_at), func.count(Review.id))
            .where(Review.user_id == user_id)
            .group_by(func.date(Review.reviewed_at))
            .order_by(func.date(Review.reviewed_at).desc())
            .limit(limit)
        )
        data = [(str(day), int(count)) for day, count in rows.all()]
        return list(reversed(data))
