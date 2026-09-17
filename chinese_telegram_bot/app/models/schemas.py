"""Pydantic schemas exchanged between importers, services and handlers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CardDraft(BaseModel):
    """A card as parsed from a dictionary file, before it hits the database."""

    model_config = ConfigDict(extra="ignore")

    hanzi: str
    pinyin: str | None = None
    translation: str | None = None
    audio: str | None = None
    example_sentence: str | None = None
    hsk_level: int | None = None
    tags: list[str] = Field(default_factory=list)
    difficulty: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewResult(BaseModel):
    """Outcome of grading a single card."""

    card_id: int | None = None
    grade: int = 0
    is_correct: bool = False
    next_due_at: datetime | None = None
    interval_days: int = 0
    ease_factor: float = 2.5
    state: str = "new"
    lapses: int = 0
    repetitions: int = 0


class AnalyticsSummary(BaseModel):
    """Aggregated progress metrics rendered by the progress screens."""

    total_cards: int = 0
    learned_cards: int = 0
    due_cards: int = 0
    streak: int = 0
    retention_rate: float = 0.0
    accuracy: float = 0.0
    weak_words: list[dict[str, Any]] = Field(default_factory=list)
    hsk_progress: dict[str, int] = Field(default_factory=dict)
    study_time_minutes: float = 0.0
    cards_per_day: float = 0.0
    monthly_progress: list[dict[str, Any]] = Field(default_factory=list)
    review_forecast: list[dict[str, Any]] = Field(default_factory=list)
    learning_speed: float = 0.0
