from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import LearningCallback
from app.keyboards.common import back_button


def learning_mode_keyboard(t) -> InlineKeyboardMarkup:
    """Modes offered in the menu.

    "Тест" (multiple choice) and "Аудирование" (listening) are hidden for now:
    the handlers are kept in the code base but the modes are not offered until
    they are finished.
    """
    builder = InlineKeyboardBuilder()
    modes = [
        ("flashcard", t("mode_flashcard")),
        ("typing", t("mode_typing")),
        ("hsk", t("mode_hsk")),
        ("random_review", t("mode_random_review")),
        ("daily_review", t("mode_daily_review")),
    ]
    for mode, label in modes:
        builder.button(text=label, callback_data=LearningCallback(action="mode", mode=mode).pack())
    back_button(builder, t)
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def rating_keyboard(t, card_id: int, mode: str) -> InlineKeyboardMarkup:
    """Self assessment for a card that is on screen: know / skip / don't know."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("learn_known"),
        callback_data=LearningCallback(action="grade", mode=mode, card_id=card_id, grade=5).pack(),
    )
    builder.button(
        text=t("learn_skip"),
        callback_data=LearningCallback(action="skip", mode=mode, card_id=card_id).pack(),
    )
    builder.button(
        text=t("learn_unknown"),
        callback_data=LearningCallback(action="grade", mode=mode, card_id=card_id, grade=1).pack(),
    )
    builder.adjust(3)
    return builder.as_markup()


def after_answer_keyboard(t) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("learn_next"), callback_data=LearningCallback(action="next").pack())
    builder.button(text=t("learn_stop"), callback_data=LearningCallback(action="stop").pack())
    builder.adjust(2)
    return builder.as_markup()
