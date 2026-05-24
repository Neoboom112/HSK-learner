from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import LanguageCallback, MenuCallback


def language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="English", callback_data=LanguageCallback(code="en").pack())
    builder.button(text="Русский", callback_data=LanguageCallback(code="ru").pack())
    builder.button(text="中文", callback_data=LanguageCallback(code="zh").pack())
    builder.adjust(1)
    return builder.as_markup()


def main_menu_keyboard(t):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu_select_dictionary"))],
            [KeyboardButton(text=t("menu_start_learning"))],
            [KeyboardButton(text=t("menu_progress"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def cancel_inline_keyboard(t):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("cancel"), callback_data=MenuCallback(action="cancel").pack())
    return builder.as_markup()
