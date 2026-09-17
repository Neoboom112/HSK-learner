"""Enumerations shared by the domain models and services."""

from __future__ import annotations

from enum import Enum


class LearningMode(str, Enum):
    """Learning modes offered on the mode keyboard."""

    FLASHCARD = "flashcard"
    TYPING = "typing"
    MULTIPLE_CHOICE = "multiple_choice"
    HSK = "hsk"
    LISTENING = "listening"
    RANDOM_REVIEW = "random_review"
    DAILY_REVIEW = "daily_review"

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.value


class DictionarySource(str, Enum):
    """Where a dictionary came from."""

    SYSTEM = "system"
    USER = "user"
    IMPORT = "import"
    HSK = "hsk"
    CSV = "csv"
    JSON = "json"
    TXT = "txt"
    APKG = "apkg"

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.value


class SRSState(str, Enum):
    """Values stored in ``cards.srs_state``."""

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.value
