from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import LearningCallback


def learning_mode_keyboard(t) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    modes = [
        ("flashcard", t("mode_flashcard")),
        ("typing", t("mode_typing")),
        ("multiple_choice", t("mode_multiple_choice")),
        ("hsk", t("mode_hsk")),
        ("listening", t("mode_listening")),
        ("random_review", t("mode_random_review")),
        ("daily_review", t("mode_daily_review")),
    ]
    for mode, label in modes:
        builder.button(text=label, callback_data=LearningCallback(action="mode", mode=mode).pack())
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def rating_keyboard(t, card_id: int, mode: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    labels = [
        (0, t("grade_0")),
        (1, t("grade_1")),
        (2, t("grade_2")),
        (3, t("grade_3")),
        (4, t("grade_4")),
        (5, t("grade_5")),
    ]
    for grade, label in labels:
        builder.button(text=label, callback_data=LearningCallback(action="grade", mode=mode, card_id=card_id, grade=grade).pack())
    builder.adjust(3, 3)
    return builder.as_markup()


def after_answer_keyboard(t) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=t("learn_next"), callback_data=LearningCallback(action="next").pack())
    builder.button(text=t("learn_stop"), callback_data=LearningCallback(action="stop").pack())
    builder.adjust(2)
    return builder.as_markup()
