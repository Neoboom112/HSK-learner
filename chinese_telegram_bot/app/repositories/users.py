from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, username: str | None, full_name: str | None, language: str) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            user.last_activity_at = datetime.now(timezone.utc)
            if changed:
                await self.session.flush()
            return user

        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            language=language,
            last_activity_at=datetime.now(timezone.utc),
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_language(self, telegram_id: int, language: str) -> None:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            return
        user.language = language
        user.last_activity_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def touch(self, telegram_id: int) -> None:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.last_activity_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def reset_counters(self, telegram_id: int) -> None:
        """Clear the aggregates that belong to the learning progress."""
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            return
        user.streak = 0
        user.total_reviews = 0
        user.total_correct = 0
        user.total_wrong = 0
        user.total_study_seconds = 0
        user.last_review_date = None
        await self.session.flush()
