"""Finite state machine states used by the handlers."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class LanguageState(StatesGroup):
    """Waiting for the user to pick an interface language."""

    choosing = State()


class DictionaryState(StatesGroup):
    """Waiting for a dictionary file upload."""

    waiting_file = State()


class LearningState(StatesGroup):
    """A learning card is on screen and awaits an answer."""

    answering = State()
