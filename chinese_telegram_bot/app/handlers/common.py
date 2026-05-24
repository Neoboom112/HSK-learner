from __future__ import annotations

from aiogram.types import Message

from app.database.models import Card, User
from app.repositories.users import UserRepository
from app.utils.text import compact_dt


async def ensure_user(session, message: Message, locale: str) -> User:
    repo = UserRepository(session)
    return await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        language=locale,
    )


def format_card(card: Card) -> str:
    parts = [f"<b>{card.hanzi}</b>"]
    if card.pinyin:
        parts.append(f"<i>{card.pinyin}</i>")
    if card.translation:
        parts.append(card.translation)
    if card.example_sentence:
        parts.append(f"Example: {card.example_sentence}")
    if card.hsk_level:
        parts.append(f"HSK {card.hsk_level}")
    if card.tags:
        parts.append("Tags: " + ", ".join(card.tags))
    parts.append(f"Due: {compact_dt(card.due_at)}")
    return "\n".join(parts)


def answer_accepted(text: str, card: Card) -> bool:
    normalized = text.strip().lower()
    answers = [card.hanzi.lower()]
    if card.translation:
        answers.append(card.translation.lower())
    if card.pinyin:
        answers.append(card.pinyin.lower())
    return any(normalized == item or normalized in item or item in normalized for item in answers if item)
