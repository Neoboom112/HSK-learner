from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from app.keyboards.common import main_menu_keyboard
from app.keyboards.dictionaries import dictionary_list_keyboard
from app.keyboards.learning import learning_mode_keyboard
from app.keyboards.progress import progress_keyboard
from app.repositories.users import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.dictionary_service import DictionaryService
from app.utils.charts import line_chart

router = Router(name=__name__)


@router.message(F.text)
async def menu_router(message: Message, session, locale: str, t, state: FSMContext) -> None:
    user = await UserRepository(session).get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        language=locale,
    )
    text = message.text.strip()
    if text == t("menu_select_dictionary"):
        dictionaries = await DictionaryService(session).list_for_user(user.id)
        if not dictionaries:
            await message.answer(t("dict_empty"))
        await message.answer(t("dict_choose_title"), reply_markup=dictionary_list_keyboard(dictionaries, t))
        return

    if text == t("menu_start_learning"):
        await message.answer(t("learn_choose_mode"), reply_markup=learning_mode_keyboard(t))
        return

    if text == t("menu_progress"):
        analytics = await AnalyticsService(session).summary(user.id)
        weak = analytics.weak_words[:5]
        weak_text = "\n".join(f"• {item['hanzi']} — {item.get('translation') or ''}" for item in weak) or t("none")
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
        monthly = analytics.monthly_progress or [{"date": "n/a", "reviews": 0}]
        labels = [row["date"][-5:] if isinstance(row["date"], str) else str(row["date"]) for row in monthly[-14:]]
        values = [row["reviews"] for row in monthly[-14:]]
        chart = line_chart(labels, values, t("progress_chart_title"), t("progress_reviews"))
        await message.answer_photo(FSInputFile(chart), caption=t("progress_chart_caption"))
        await message.answer(summary, reply_markup=progress_keyboard(t))
        return

    await message.answer(t("unknown_command"), reply_markup=main_menu_keyboard(t))
