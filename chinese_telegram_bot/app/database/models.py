"""ORM models mirroring ``migrations/versions/0001_init.py``.

The public attribute names match what the repositories, services and handlers
already use (``card.metadata``, ``dictionary.meta``, ``setting.key`` ...).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import (
    Base,
    IdMixin,
    TimestampMixin,
    UTCDateTime,
    metadata_alias,
    utcnow,
)

__all__ = [
    "Card",
    "Dictionary",
    "LearningSession",
    "Review",
    "ScheduledReview",
    "Setting",
    "Statistic",
    "User",
]


class User(IdMixin, TimestampMixin, Base):
    """A Telegram user of the bot."""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(8), default="en", server_default=text("'en'"), nullable=False)
    active_dictionary_id: Mapped[int | None] = mapped_column(Integer)
    streak: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_review_date: Mapped[datetime | None] = mapped_column(UTCDateTime())
    total_study_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    total_correct: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    total_wrong: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)


class Dictionary(IdMixin, TimestampMixin, Base):
    """A deck of cards, either shipped with the bot or uploaded by a user."""

    __tablename__ = "dictionaries"

    owner_user_id: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(32), default="system", server_default=text("'system'"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(8), default="zh", server_default=text("'zh'"), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Card(IdMixin, TimestampMixin, Base):
    """A single flashcard plus its spaced repetition scheduling state."""

    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("user_id", "duplicate_hash", name="uq_cards_user_duplicate_hash"),
    )

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dictionary_id: Mapped[int] = mapped_column(Integer, nullable=False)
    hanzi: Mapped[str] = mapped_column(String(255), nullable=False)
    pinyin: Mapped[str | None] = mapped_column(String(255))
    translation: Mapped[str | None] = mapped_column(Text)
    audio: Mapped[str | None] = mapped_column(Text)
    example_sentence: Mapped[str | None] = mapped_column(Text)
    hsk_level: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"), nullable=False)
    custom_metadata: Mapped[dict[str, Any]] = mapped_column(
        "custom_metadata", JSON, default=dict, nullable=False
    )
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, server_default=text("2.5"), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    stability: Mapped[float] = mapped_column(Float, default=0.0, server_default=text("0.0"), nullable=False)
    srs_state: Mapped[str] = mapped_column(
        String(32), default="new", server_default=text("'new'"), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    suspended: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"), nullable=False)
    is_leech: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"), nullable=False)
    duplicate_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class Review(IdMixin, TimestampMixin, Base):
    """One answered card."""

    __tablename__ = "reviews"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    review_metadata: Mapped[dict[str, Any]] = mapped_column(
        "review_metadata", JSON, default=dict, nullable=False
    )


class Statistic(IdMixin, TimestampMixin, Base):
    """Daily rollup of a user's activity."""

    __tablename__ = "statistics"
    __table_args__ = (UniqueConstraint("user_id", "stat_date", name="uq_stats_user_date"),)

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_date: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    cards_learned: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    reviews_done: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    study_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class LearningSession(IdMixin, TimestampMixin, Base):
    """A learning session started from the mode keyboard."""

    __tablename__ = "learning_sessions"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    cards_seen: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    wrong_answers: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    session_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)


class Setting(IdMixin, TimestampMixin, Base):
    """Key/value user preference."""

    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_settings_user_key"),)

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class ScheduledReview(IdMixin, TimestampMixin, Base):
    """Reminder bookkeeping for the review scheduler."""

    __tablename__ = "scheduled_reviews"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)
    due_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(
        String(32), default="pending", server_default=text("'pending'"), nullable=False
    )
    reminder_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)


# ``Card(...)``/``Review(...)``/... are constructed and read through the
# ``metadata`` attribute, so re-expose the JSON columns under that name.
Card.metadata = metadata_alias("custom_metadata")
Review.metadata = metadata_alias("review_metadata")
LearningSession.metadata = metadata_alias("session_metadata")
ScheduledReview.metadata = metadata_alias("reminder_metadata")
