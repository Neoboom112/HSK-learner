from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card
from app.models.schemas import CardDraft
from app.utils.validators import fingerprint_card


class CardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_for_user(self, user_id: int) -> int:
        result = await self.session.execute(select(func.count(Card.id)).where(Card.user_id == user_id))
        return int(result.scalar_one())

    async def count_learned(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(Card.id)).where(Card.user_id == user_id, Card.repetitions > 0)
        )
        return int(result.scalar_one())

    async def bulk_upsert(
        self,
        user_id: int,
        dictionary_id: int,
        items: list[CardDraft],
    ) -> tuple[int, int]:
        imported = 0
        duplicates = 0
        for item in items:
            duplicate_hash = fingerprint_card(item.hanzi, item.pinyin, item.translation)
            result = await self.session.execute(
                select(Card).where(Card.user_id == user_id, Card.duplicate_hash == duplicate_hash)
            )
            exists = result.scalar_one_or_none()
            if exists:
                duplicates += 1
                continue
            card = Card(
                user_id=user_id,
                dictionary_id=dictionary_id,
                hanzi=item.hanzi,
                pinyin=item.pinyin,
                translation=item.translation,
                audio=item.audio,
                example_sentence=item.example_sentence,
                hsk_level=item.hsk_level,
                tags=item.tags,
                difficulty=item.difficulty,
                metadata=item.metadata,
                duplicate_hash=duplicate_hash,
                due_at=datetime.now(timezone.utc),
            )
            self.session.add(card)
            imported += 1
        await self.session.flush()
        return imported, duplicates

    async def get_by_id(self, card_id: int) -> Card | None:
        result = await self.session.execute(select(Card).where(Card.id == card_id))
        return result.scalar_one_or_none()

    async def get_due_cards(self, user_id: int, limit: int = 20) -> list[Card]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Card)
            .where(
                Card.user_id == user_id,
                Card.suspended.is_(False),
                Card.due_at <= now,
            )
            .order_by(Card.due_at.asc(), Card.repetitions.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_random_cards(self, user_id: int, limit: int = 20, hsk_level: int | None = None) -> list[Card]:
        stmt = select(Card).where(Card.user_id == user_id, Card.suspended.is_(False))
        if hsk_level is not None:
            stmt = stmt.where(Card.hsk_level == hsk_level)
        stmt = stmt.order_by(func.random()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_weak_cards(self, user_id: int, limit: int = 20) -> list[Card]:
        result = await self.session.execute(
            select(Card)
            .where(Card.user_id == user_id, Card.repetitions > 0)
            .order_by(Card.lapses.desc(), Card.ease_factor.asc(), Card.interval_days.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_hsk_progress(self, user_id: int) -> dict[str, int]:
        rows = await self.session.execute(
            select(Card.hsk_level, func.count(Card.id))
            .where(Card.user_id == user_id)
            .group_by(Card.hsk_level)
        )
        progress: dict[str, int] = {}
        for level, count in rows.all():
            key = f"HSK{level}" if level else "Unsorted"
            progress[key] = int(count)
        return progress

    async def get_forecast(self, user_id: int, days: int = 14) -> list[dict[str, int]]:
        forecast: list[dict[str, int]] = []
        now = datetime.now(timezone.utc)
        cards = await self.get_random_cards(user_id, limit=500)
        for offset in range(days):
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=offset)
            day_end = day_start + timedelta(days=1)
            amount = sum(1 for card in cards if day_start <= card.due_at < day_end)
            forecast.append({"day": day_start.strftime("%Y-%m-%d"), "cards": amount})
        return forecast

    async def search_by_text(self, user_id: int, text: str) -> list[Card]:
        like = f"%{text}%"
        result = await self.session.execute(
            select(Card).where(
                Card.user_id == user_id,
                or_(Card.hanzi.like(like), Card.pinyin.like(like), Card.translation.like(like)),
            ).limit(20)
        )
        return list(result.scalars().all())
