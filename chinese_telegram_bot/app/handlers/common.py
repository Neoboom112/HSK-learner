from __future__ import annotations

import re
import unicodedata

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from app.database.models import Card, User
from app.repositories.users import UserRepository
from app.utils.text import compact_dt

_ANSWER_SPLIT_RE = re.compile(r"[;,/、]|(?:\s+-\s+)")
_NOISE_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_ARTICLES = ("to ", "a ", "an ", "the ")


def _normalize_answer(value: str) -> str:
    """Lower case, drop punctuation and squeeze spaces."""
    text = value.casefold().replace("ё", "е")
    text = _NOISE_RE.sub(" ", text)
    return " ".join(text.split())


def _without_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _answer_variants(card: Card) -> set[str]:
    variants: set[str] = set()
    for value in (card.hanzi, card.translation, card.pinyin):
        if not value:
            continue
        variants.add(_normalize_answer(value))
        for part in _ANSWER_SPLIT_RE.split(value):
            variants.add(_normalize_answer(part))
    if card.pinyin:
        plain = _normalize_answer(_without_diacritics(card.pinyin))
        variants.add(plain)
        variants.add(plain.replace(" ", ""))
    for value in list(variants):
        for article in _ARTICLES:
            if value.startswith(article):
                variants.add(value[len(article):])
    variants.discard("")
    return variants


def answer_accepted(text: str, card: Card) -> bool:
    """Compare a typed answer with the card, forgiving variants and tone marks."""
    answer = _normalize_answer(text or "")
    if not answer:
        return False

    variants = _answer_variants(card)
    if answer in variants:
        return True

    compact = answer.replace(" ", "")
    for variant in variants:
        if len(variant) >= 2 and (variant in answer or answer in variant):
            return True
        squashed = variant.replace(" ", "")
        if len(squashed) >= 2 and (squashed in compact or compact in squashed):
            return True
    return False


async def edit_or_send(message: Message, text: str, **kwargs) -> None:
    """Edit the message, or send a new one when it has no text to edit."""
    if message.text is None and message.caption is None:
        await message.answer(text, **kwargs)
        return
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest:
        await message.answer(text, **kwargs)


async def ensure_user(session, message: Message, locale: str) -> User:
    repo = UserRepository(session)
    return await repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        language=locale,
    )


def format_card(card: Card, include_translation: bool = True) -> str:
    """Render a card.  The translation is hidden while the answer is pending."""
    parts = [f"<b>{card.hanzi}</b>"]
    if card.pinyin:
        parts.append(f"<i>{card.pinyin}</i>")
    if include_translation and card.translation:
        parts.append(card.translation)
    if card.example_sentence:
        parts.append(f"Example: {card.example_sentence}")
    if card.hsk_level:
        parts.append(f"HSK {card.hsk_level}")
    if card.tags:
        parts.append("Tags: " + ", ".join(card.tags))
    parts.append(f"Due: {compact_dt(card.due_at)}")
    return "\n".join(parts)
