"""Typed ``callback_data`` factories shared by keyboards and handlers."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class LanguageCallback(CallbackData, prefix="lang"):
    """Interface language picked on the onboarding screen."""

    code: str


class MenuCallback(CallbackData, prefix="menu"):
    """Generic menu action (for example ``cancel``)."""

    action: str


class LearningCallback(CallbackData, prefix="learn"):
    """Learning flow actions: choosing a mode, grading a card, continuing."""

    action: str
    mode: str | None = None
    card_id: int | None = None
    grade: int | None = None


class DictionaryCallback(CallbackData, prefix="dict"):
    """Dictionary selection and import entry points."""

    action: str
    dictionary_id: int | None = None


class ProgressCallback(CallbackData, prefix="prog"):
    """Progress dashboard actions, including the export buttons."""

    action: str
