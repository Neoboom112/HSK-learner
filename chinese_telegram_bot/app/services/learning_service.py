from __future__ import annotations

from collections.abc import Iterable
from random import choice

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card
from app.models.enums import LearningMode
from app.repositories.cards import CardRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.sessions import SessionRepository
from app.services.srs_service import SRSService


class LearningService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cards = CardRepository(session)
        self.reviews = ReviewRepository(session)
        self.sessions = SessionRepository(session)
        self.srs = SRSService()

    async def start_session(self, user_id: int, mode: LearningMode) -> int:
        session = await self.sessions.start(user_id=user_id, mode=mode.value)
        return session.id

    async def next_card(
        self,
        user_id: int,
        mode: LearningMode,
        exclude: Iterable[int] | None = None,
        dictionary_id: int | None = None,
    ) -> Card | None:
        """Pick the next card.

        ``exclude`` drops ids already skipped in this session, ``dictionary_id``
        limits the choice to one deck (``None`` means every deck of the user).
        """
        excluded = {int(card_id) for card_id in (exclude or ())}

        def usable(cards: list[Card]) -> list[Card]:
            return [card for card in cards if card.id not in excluded]

        if mode in {LearningMode.DAILY_REVIEW, LearningMode.RANDOM_REVIEW}:
            limit = 1 if mode == LearningMode.DAILY_REVIEW else 20
            due_cards = usable(
                await self.cards.get_due_cards(user_id, limit=limit, dictionary_id=dictionary_id)
            )
            if due_cards:
                return due_cards[0] if mode == LearningMode.DAILY_REVIEW else choice(due_cards)

        due = usable(await self.cards.get_due_cards(user_id, limit=20, dictionary_id=dictionary_id))
        if due:
            return choice(due)

        rest = usable(
            await self.cards.get_random_cards(user_id, limit=20, dictionary_id=dictionary_id)
        )
        return choice(rest) if rest else None

    async def answer(self, user_id: int, card_id: int, grade: int, mode: LearningMode, response_time_ms: int | None = None) -> tuple[Card, bool]:
        # Only cards of this user may be graded: a crafted callback must not be
        # able to touch (or reveal) somebody else's card.
        card = await self.cards.get_by_id(card_id, user_id)
        if card is None:
            raise ValueError("Card not found")
        update = self.srs.review(card, grade)
        await self.reviews.add(
            user_id=user_id,
            card_id=card.id,
            grade=grade,
            is_correct=update.is_correct,
            mode=mode.value,
            response_time_ms=response_time_ms,
            metadata={"next_due_at": update.next_due_at.isoformat(), "ease_factor": update.ease_factor},
        )
        return card, update.is_correct

    async def finish_session(self, session_id: int, cards_seen: int, correct_answers: int, wrong_answers: int, duration_seconds: int) -> None:
        await self.sessions.finish(
            session_id,
            cards_seen=cards_seen,
            correct_answers=correct_answers,
            wrong_answers=wrong_answers,
            metadata={"duration_seconds": duration_seconds},
        )
