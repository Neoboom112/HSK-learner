from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import MenuCallback, ProgressCallback
from app.keyboards.common import back_button


def progress_keyboard(t):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("progress_export_json"), callback_data=ProgressCallback(action="export_json").pack())
    builder.button(text=t("progress_export_csv"), callback_data=ProgressCallback(action="export_csv").pack())
    builder.button(text=t("progress_export_apkg"), callback_data=ProgressCallback(action="export_apkg").pack())
    builder.button(text=t("progress_reset"), callback_data=ProgressCallback(action="reset").pack())
    back_button(builder, t)
    builder.adjust(1)
    return builder.as_markup()


def reset_confirm_keyboard(t):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("progress_reset_yes"),
        callback_data=ProgressCallback(action="reset_confirm").pack(),
    )
    builder.button(text=t("cancel"), callback_data=MenuCallback(action="menu").pack())
    builder.adjust(1)
    return builder.as_markup()
