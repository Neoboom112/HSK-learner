from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import DictionaryCallback


def dictionary_list_keyboard(dictionaries, t):
    builder = InlineKeyboardBuilder()
    for item in dictionaries:
        label = item.name
        if item.is_system:
            label += f" · {t('system_badge')}"
        builder.button(text=label, callback_data=DictionaryCallback(action="select", dictionary_id=item.id).pack())
    builder.button(text=t("dict_upload"), callback_data=DictionaryCallback(action="upload").pack())
    builder.button(text=t("dict_import_hsk"), callback_data=DictionaryCallback(action="import_hsk").pack())
    builder.button(text=t("dict_import_csv"), callback_data=DictionaryCallback(action="import_csv").pack())
    builder.button(text=t("dict_import_json"), callback_data=DictionaryCallback(action="import_json").pack())
    builder.button(text=t("dict_import_txt"), callback_data=DictionaryCallback(action="import_txt").pack())
    builder.button(text=t("dict_import_apkg"), callback_data=DictionaryCallback(action="import_apkg").pack())
    builder.adjust(1)
    return builder.as_markup()
