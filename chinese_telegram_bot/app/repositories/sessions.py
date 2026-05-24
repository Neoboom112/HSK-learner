from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import LearningSession


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start(self, user_id: int, mode: str, metadata: dict | None = None) -> LearningSession:
        learning_session = LearningSession(
            user_id=user_id,
            mode=mode,
            metadata=metadata or {},
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(learning_session)
        await self.session.flush()
        return learning_session

    async def finish(self, session_id: int, cards_seen: int, correct_answers: int, wrong_answers: int, metadata: dict | None = None) -> None:
        result = await self.session.execute(select(LearningSession).where(LearningSession.id == session_id))
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.ended_at = datetime.now(timezone.utc)
        row.cards_seen = cards_seen
        row.correct_answers = correct_answers
        row.wrong_answers = wrong_answers
        if metadata:
            row.metadata = {**row.metadata, **metadata}
        await self.session.flush()

    async def active_session(self, user_id: int) -> LearningSession | None:
        result = await self.session.execute(
            select(LearningSession)
            .where(LearningSession.user_id == user_id, LearningSession.ended_at.is_(None))
            .order_by(LearningSession.started_at.desc())
        )
        return result.scalar_one_or_none()
