from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Document, Message

from app.callbacks import DictionaryCallback
from app.config import get_settings
from app.keyboards.common import main_menu_keyboard
from app.keyboards.dictionaries import dictionary_list_keyboard
from app.repositories.dictionaries import DictionaryRepository
from app.repositories.users import UserRepository
from app.services.dictionary_service import DictionaryService
from app.states import DictionaryState
from app.utils.constants import SUPPORTED_EXTENSIONS

router = Router(name=__name__)


@router.callback_query(DictionaryCallback.filter(F.action == "select"))
async def select_dictionary(callback: CallbackQuery, callback_data: DictionaryCallback, session, t, locale: str) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    dictionary = await DictionaryRepository(session).get(callback_data.dictionary_id)
    if dictionary is None:
        await callback.answer(t("dict_not_found"), show_alert=True)
        return

    if dictionary.is_system:
        await DictionaryService(session).clone_system_dictionary(user.id, dictionary)

    user.active_dictionary_id = dictionary.id
    await session.flush()
    await callback.message.edit_text(t("dict_selected", name=dictionary.name))
    await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
    await callback.answer()


@router.callback_query(DictionaryCallback.filter(F.action.in_({"upload", "import_hsk", "import_csv", "import_json", "import_txt", "import_apkg"})))
async def import_dictionary_entry(callback: CallbackQuery, callback_data: DictionaryCallback, state: FSMContext, t) -> None:
    await state.set_state(DictionaryState.waiting_file)
    await state.update_data(import_kind=callback_data.action)
    await callback.message.edit_text(t("dict_upload_prompt"))
    await callback.answer()


@router.message(DictionaryState.waiting_file, F.document)
async def handle_dictionary_file(message: Message, session, state: FSMContext, t, locale: str) -> None:
    document: Document = message.document
    settings = get_settings()
    ext = Path(document.file_name or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        await message.answer(t("dict_unsupported_format"))
        return

    if document.file_size and document.file_size > settings.max_upload_mb * 1024 * 1024:
        await message.answer(t("dict_file_too_large", mb=settings.max_upload_mb))
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
    dictionary, imported, duplicates = await service.import_file(
        user=user,
        filename=document.file_name or f"import{ext}",
        payload=content,
        dictionary_name=Path(document.file_name or "dictionary").stem,
    )
    user.active_dictionary_id = dictionary.id
    await session.flush()
    await state.clear()
    await message.answer(
        t("dict_import_done", name=dictionary.name, imported=imported, duplicates=duplicates),
        reply_markup=main_menu_keyboard(t),
    )


@router.message(DictionaryState.waiting_file)
async def handle_dictionary_text(message: Message, t) -> None:
    await message.answer(t("dict_send_file"))
