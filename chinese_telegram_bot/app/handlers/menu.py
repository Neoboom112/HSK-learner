from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.callbacks import MenuCallback
from app.handlers.common import edit_or_send
from app.keyboards.common import main_menu_keyboard
from app.keyboards.dictionaries import dictionary_list_keyboard
from app.keyboards.learning import learning_mode_keyboard
from app.keyboards.progress import progress_keyboard
from app.repositories.users import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.dictionary_service import DictionaryService
from app.utils.charts import reviews_chart

router = Router(name=__name__)


async def get_user(session, from_user, locale: str):
    return await UserRepository(session).get_or_create(
        telegram_id=from_user.id,
        username=from_user.username,
        full_name=from_user.full_name,
        language=locale,
    )


async def send_dictionary_list(message: Message, session, t, user) -> None:
    dictionaries = await DictionaryService(session).list_for_user(user.id)
    if not dictionaries:
        await message.answer(t("dict_empty"))
    await message.answer(
        f"{t('dict_choose_title')}\n\n{t('dict_import_hint')}",
        reply_markup=dictionary_list_keyboard(dictionaries, t, active_id=user.active_dictionary_id),
    )


async def send_progress(message: Message, session, t, user) -> None:
    analytics = await AnalyticsService(session).summary(user.id)
    weak = analytics.weak_words[:5]
    weak_text = (
        "\n".join(
            f"• {item['hanzi']} — {item.get('translation') or '—'}"
            + (f" ⚠{item['lapses']}" if item.get("lapses") else "")
            for item in weak
        )
        or t("none")
    )
    summary = (
        f"{t('progress_title')}\n\n"
        f"{t('progress_total_cards')}: <b>{analytics.total_cards}</b>\n"
        f"{t('progress_learned')}: <b>{analytics.learned_cards}</b>\n"
        f"{t('progress_due')}: <b>{analytics.due_cards}</b>\n"
        f"{t('progress_streak')}: <b>{analytics.streak}</b>\n"
        f"{t('progress_accuracy')}: <b>{analytics.accuracy:.1f}%</b>\n"
        f"{t('progress_retention')}: <b>{analytics.retention_rate:.1f}%</b>\n"
        f"{t('progress_study_time')}: <b>{analytics.study_time_minutes:.1f}m</b>\n\n"
        f"{t('progress_weak_words')}:\n{weak_text}"
    )
    chart = reviews_chart(
        analytics.monthly_progress,
        t("progress_chart_title"),
        t("progress_reviews"),
        t("progress_chart_empty"),
    )
    await message.answer_photo(FSInputFile(chart), caption=t("progress_chart_caption"))
    await message.answer(summary, reply_markup=progress_keyboard(t))


@router.message(Command("menu"))
async def cmd_menu(message: Message, session, locale: str, t, state: FSMContext) -> None:
    await state.clear()
    await get_user(session, message.from_user, locale)
    await message.answer(t("welcome_back"), reply_markup=main_menu_keyboard(t))


@router.message(Command("dictionary"))
async def cmd_dictionary(message: Message, session, locale: str, t, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(session, message.from_user, locale)
    await send_dictionary_list(message, session, t, user)


@router.message(Command("progress"))
async def cmd_progress(message: Message, session, locale: str, t, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(session, message.from_user, locale)
    await send_progress(message, session, t, user)


@router.message(Command("help"))
async def cmd_help(message: Message, t) -> None:
    await message.answer(t("help_text"), reply_markup=main_menu_keyboard(t))


@router.callback_query(MenuCallback.filter(F.action.in_({"menu", "cancel"})))
async def back_to_menu(callback: CallbackQuery, t, state: FSMContext) -> None:
    await state.clear()
    await edit_or_send(callback.message, t("back_to_menu"))
    await callback.message.answer(t("welcome_back"), reply_markup=main_menu_keyboard(t))
    await callback.answer()


@router.message(F.text)
async def menu_router(message: Message, session, locale: str, t, state: FSMContext) -> None:
    user = await get_user(session, message.from_user, locale)
    text = message.text.strip()

    if text == t("menu_select_dictionary"):
        await state.clear()
        await send_dictionary_list(message, session, t, user)
        return

    if text == t("menu_start_learning"):
        await state.clear()
        await message.answer(t("learn_choose_mode"), reply_markup=learning_mode_keyboard(t))
        return

    if text == t("menu_progress"):
        await state.clear()
        await send_progress(message, session, t, user)
        return

    if text == t("menu_help"):
        await message.answer(t("help_text"), reply_markup=main_menu_keyboard(t))
        return

    await message.answer(t("unknown_command"), reply_markup=main_menu_keyboard(t))
