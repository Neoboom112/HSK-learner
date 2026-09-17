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
            [KeyboardButton(text=t("menu_help"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def back_button(builder: InlineKeyboardBuilder, t) -> InlineKeyboardBuilder:
    """Append the shared "back to menu" button to an inline keyboard."""
    builder.button(text=t("back"), callback_data=MenuCallback(action="menu").pack())
    return builder


def back_keyboard(t):
    """A keyboard that only offers the way back to the main menu."""
    return back_button(InlineKeyboardBuilder(), t).as_markup()


def cancel_inline_keyboard(t):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("cancel"), callback_data=MenuCallback(action="cancel").pack())
    builder.adjust(1)
    return builder.as_markup()
