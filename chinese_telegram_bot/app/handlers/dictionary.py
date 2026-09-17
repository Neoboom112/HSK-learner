from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, Message

from app.callbacks import DictionaryCallback
from app.config import get_settings
from app.handlers.common import edit_or_send
from app.keyboards.common import main_menu_keyboard
from app.keyboards.dictionaries import (
    delete_confirm_keyboard,
    delete_dictionary_keyboard,
    import_retry_keyboard,
)
from app.repositories.dictionaries import DictionaryRepository
from app.repositories.users import UserRepository
from app.services.dictionary_service import DictionaryService
from app.states import DictionaryState
from app.utils.constants import SUPPORTED_EXTENSIONS

router = Router(name=__name__)

IMPORT_ACTIONS = {"upload", "import_hsk", "import_csv", "import_json", "import_txt", "import_apkg"}


@router.callback_query(DictionaryCallback.filter(F.action == "select"))
async def select_dictionary(callback: CallbackQuery, callback_data: DictionaryCallback, session, t, locale: str) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    dictionary = await DictionaryRepository(session).get(callback_data.dictionary_id)
    # A crafted callback must not be able to select somebody else's dictionary.
    if dictionary is None or (not dictionary.is_system and dictionary.owner_user_id != user.id):
        await callback.answer(t("dict_not_found"), show_alert=True)
        return

    if dictionary.is_system:
        await DictionaryService(session).clone_system_dictionary(user.id, dictionary)

    user.active_dictionary_id = dictionary.id
    await session.flush()
    await edit_or_send(callback.message, t("dict_selected", name=dictionary.name))
    await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
    await callback.answer()


@router.callback_query(DictionaryCallback.filter(F.action == "all"))
async def select_all_dictionaries(callback: CallbackQuery, session, t, locale: str) -> None:
    """Review every deck of the user instead of a single one."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    user.active_dictionary_id = None
    await session.flush()
    await edit_or_send(callback.message, t("dict_selected_all"))
    await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
    await callback.answer()


@router.callback_query(DictionaryCallback.filter(F.action == "delete_menu"))
async def delete_dictionary_menu(callback: CallbackQuery, session, t, locale: str) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    own = [
        dictionary
        for dictionary in await DictionaryService(session).list_for_user(user.id)
        if not dictionary.is_system
    ]
    if not own:
        await edit_or_send(callback.message, t("dict_delete_empty"))
    else:
        await edit_or_send(
            callback.message,
            t("dict_delete_choose"),
            reply_markup=delete_dictionary_keyboard(own, t),
        )
    await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
    await callback.answer()


@router.callback_query(DictionaryCallback.filter(F.action == "delete"))
async def delete_dictionary_ask(callback: CallbackQuery, callback_data: DictionaryCallback, session, t, locale: str) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    dictionary = await DictionaryRepository(session).get(callback_data.dictionary_id)
    if dictionary is None or dictionary.is_system or dictionary.owner_user_id != user.id:
        await callback.answer(t("dict_not_found"), show_alert=True)
        return
    cards = await DictionaryService(session).count_cards(user.id, dictionary.id)
    await edit_or_send(
        callback.message,
        t("dict_delete_ask", name=dictionary.name, cards=cards),
        reply_markup=delete_confirm_keyboard(t, dictionary.id),
    )
    await callback.answer()


@router.callback_query(DictionaryCallback.filter(F.action == "delete_confirm"))
async def delete_dictionary_confirm(callback: CallbackQuery, callback_data: DictionaryCallback, session, t, locale: str) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    dictionary = await DictionaryRepository(session).get(callback_data.dictionary_id)
    if dictionary is None or dictionary.is_system or dictionary.owner_user_id != user.id:
        await callback.answer(t("dict_not_found"), show_alert=True)
        return

    name = dictionary.name
    if user.active_dictionary_id == dictionary.id:
        user.active_dictionary_id = None
        await session.flush()

    cards, reviews = await DictionaryService(session).delete_user_dictionary(user.id, dictionary)
    await edit_or_send(callback.message, t("dict_delete_done", name=name, cards=cards, reviews=reviews))
    await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
    await callback.answer()


@router.callback_query(DictionaryCallback.filter(F.action.in_(IMPORT_ACTIONS)))
async def import_dictionary_entry(callback: CallbackQuery, callback_data: DictionaryCallback, state: FSMContext, t) -> None:
    await state.set_state(DictionaryState.waiting_file)
    await state.update_data(import_kind=callback_data.action)
    # Every entry explains which file it expects.
    prompt = t("dict_txt_prompt") if callback_data.action == "import_txt" else t("dict_upload_prompt")
    await edit_or_send(
        callback.message,
        prompt,
        reply_markup=import_retry_keyboard(t, callback_data.action),
    )
    await callback.answer()


@router.message(DictionaryState.waiting_file, F.document)
async def handle_dictionary_file(message: Message, session, state: FSMContext, t, locale: str) -> None:
    document: Document = message.document
    settings = get_settings()
    kind = (await state.get_data()).get("import_kind") or "upload"
    ext = Path(document.file_name or "").suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        await message.answer(t("dict_unsupported_format"), reply_markup=import_retry_keyboard(t, kind))
        return

    if document.file_size and document.file_size > settings.max_upload_mb * 1024 * 1024:
        await message.answer(
            t("dict_file_too_large", mb=settings.max_upload_mb),
            reply_markup=import_retry_keyboard(t, kind),
        )
        return

    file = await message.bot.get_file(document.file_id)
    payload = await message.bot.download_file(file.file_path)
    content = payload.read()

    service = DictionaryService(session)
    user = await UserRepository(session).get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        language=locale,
    )
    try:
        dictionary, imported, duplicates = await service.import_file(
            user=user,
            filename=document.file_name or f"import{ext}",
            payload=content,
            dictionary_name=Path(document.file_name or "dictionary").stem,
        )
    except ValueError as exc:
        # Broken archives, unsupported layouts or empty decks: explain the reason
        # and keep the state, so the user can resend a file straight away.
        await message.answer(
            t("dict_import_error", error=exc),
            reply_markup=import_retry_keyboard(t, kind),
        )
        return

    user.active_dictionary_id = dictionary.id
    await session.flush()
    await state.clear()
    await message.answer(
        t("dict_import_done", name=dictionary.name, imported=imported, duplicates=duplicates),
        reply_markup=main_menu_keyboard(t),
    )


@router.message(DictionaryState.waiting_file)
async def handle_dictionary_text(message: Message, state: FSMContext, t) -> None:
    kind = (await state.get_data()).get("import_kind") or "upload"
    await message.answer(t("dict_retry"), reply_markup=import_retry_keyboard(t, kind))
