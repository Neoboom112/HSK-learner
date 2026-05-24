from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import ProgressCallback


def progress_keyboard(t):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("progress_export_json"), callback_data=ProgressCallback(action="export_json").pack())
    builder.button(text=t("progress_export_csv"), callback_data=ProgressCallback(action="export_csv").pack())
    builder.button(text=t("progress_export_apkg"), callback_data=ProgressCallback(action="export_apkg").pack())
    builder.adjust(1)
    return builder.as_markup()
