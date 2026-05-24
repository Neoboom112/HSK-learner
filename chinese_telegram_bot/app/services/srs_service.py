from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.database.models import Card
from app.models.schemas import ReviewResult


@dataclass(slots=True)
class SRSUpdate:
    card: Card
    grade: int
    is_correct: bool
    next_due_at: datetime
    interval_days: int
    ease_factor: float
    state: str


class SRSService:
    def __init__(self) -> None:
        self.learning_steps = [timedelta(minutes=10), timedelta(days=1)]

    def review(self, card: Card, grade: int) -> SRSUpdate:
        grade = max(0, min(5, int(grade)))
        now = datetime.now(timezone.utc)
        overdue_days = max(0, (now - card.due_at).days) if card.due_at else 0

        if grade < 3:
            card.lapses += 1
            card.repetitions = 0
            card.interval_days = 1
            card.ease_factor = max(1.3, card.ease_factor - 0.2)
            card.stability = max(0.0, card.stability * 0.6)
            card.srs_state = "relearning"
            card.due_at = now + timedelta(days=1)
            card.last_reviewed_at = now
            card.difficulty = min(10, card.difficulty + 1)
            return self._build(card, grade, False)

        if card.repetitions == 0:
            interval = 1
            state = "learning"
        elif card.repetitions == 1:
            interval = 6
            state = "review"
        else:
            interval = max(1, round(card.interval_days * card.ease_factor))
            state = "review"

        if overdue_days > 0:
            interval = max(interval, round(interval + overdue_days / 2))

        card.repetitions += 1
        card.ease_factor = max(1.3, card.ease_factor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)))
        card.interval_days = interval
        card.stability = min(3650.0, max(card.stability, 1.0) * card.ease_factor)
        card.srs_state = state
        card.due_at = now + timedelta(days=interval)
        card.last_reviewed_at = now
        card.difficulty = max(1, min(10, card.difficulty - 1 if grade >= 4 else card.difficulty))
        return self._build(card, grade, True)

    def _build(self, card: Card, grade: int, is_correct: bool) -> SRSUpdate:
        return SRSUpdate(
            card=card,
            grade=grade,
            is_correct=is_correct,
            next_due_at=card.due_at,
            interval_days=card.interval_days,
            ease_factor=card.ease_factor,
            state=card.srs_state,
        )
