from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import DictionaryCallback
from app.keyboards.common import back_button


def dictionary_list_keyboard(dictionaries, t, active_id: int | None = None):
    """Dictionary screen: the deck list plus the import and delete entries.

    ``active_id`` marks the deck used for reviews, ``None`` means all of them.
    """
    builder = InlineKeyboardBuilder()

    all_label = t("dict_all") if active_id is not None else f"✅ {t('dict_all')}"
    builder.button(text=all_label, callback_data=DictionaryCallback(action="all").pack())

    for item in dictionaries:
        label = item.name
        if item.is_system:
            label += f" · {t('system_badge')}"
        if active_id is not None and item.id == active_id:
            label = f"✅ {label}"
        builder.button(text=label, callback_data=DictionaryCallback(action="select", dictionary_id=item.id).pack())

    builder.button(text=t("dict_import_apkg"), callback_data=DictionaryCallback(action="import_apkg").pack())
    builder.button(text=t("dict_import_txt"), callback_data=DictionaryCallback(action="import_txt").pack())
    builder.button(text=t("dict_delete"), callback_data=DictionaryCallback(action="delete_menu").pack())
    back_button(builder, t)
    builder.adjust(1)
    return builder.as_markup()


def delete_dictionary_keyboard(dictionaries, t):
    """Pick which of the user's own dictionaries to delete."""
    builder = InlineKeyboardBuilder()
    for item in dictionaries:
        builder.button(
            text=item.name,
            callback_data=DictionaryCallback(action="delete", dictionary_id=item.id).pack(),
        )
    back_button(builder, t)
    builder.adjust(1)
    return builder.as_markup()


def delete_confirm_keyboard(t, dictionary_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("dict_delete_yes"),
        callback_data=DictionaryCallback(action="delete_confirm", dictionary_id=dictionary_id).pack(),
    )
    back_button(builder, t)
    builder.adjust(1)
    return builder.as_markup()


def import_retry_keyboard(t, kind: str = "import_apkg"):
    """Offered after a failed upload so the user can retry without typing."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("retry"), callback_data=DictionaryCallback(action=kind).pack())
    back_button(builder, t)
    builder.adjust(1)
    return builder.as_markup()
