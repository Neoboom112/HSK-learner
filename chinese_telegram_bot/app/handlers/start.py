from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.callbacks import LanguageCallback
from app.i18n import get_localizer
from app.keyboards.common import language_keyboard, main_menu_keyboard
from app.repositories.users import UserRepository
from app.states import LanguageState

router = Router(name=__name__)


@router.message(CommandStart())
async def start(message: Message, session, locale: str, t, state: FSMContext) -> None:
    await state.clear()
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user is None or not user.language:
        await state.set_state(LanguageState.choosing)
        await message.answer(t("choose_language"), reply_markup=language_keyboard())
        return
    await message.answer(t("welcome_back"), reply_markup=main_menu_keyboard(t))


@router.callback_query(LanguageCallback.filter())
async def choose_language(callback: CallbackQuery, callback_data: LanguageCallback, session, state: FSMContext) -> None:
    localizer = get_localizer(callback_data.code)
    t = localizer.t
    repo = UserRepository(session)
    await repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
        language=callback_data.code,
    )
    await repo.set_language(callback.from_user.id, callback_data.code)
    await state.clear()
    await callback.message.edit_text(t("language_set", language=callback_data.code))
    await callback.message.answer(t("welcome"), reply_markup=main_menu_keyboard(t))
    await callback.answer()
