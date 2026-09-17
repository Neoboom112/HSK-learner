from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

from app.callbacks import ProgressCallback
from app.config import get_settings
from app.handlers.common import edit_or_send
from app.keyboards.common import main_menu_keyboard
from app.keyboards.progress import reset_confirm_keyboard
from app.repositories.cards import CardRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.statistics import StatisticsRepository
from app.repositories.users import UserRepository
from app.services.export_service import ExportService

router = Router(name=__name__)


@router.callback_query(ProgressCallback.filter(F.action.startswith("export_")))
async def export_progress(callback: CallbackQuery, callback_data: ProgressCallback, session, t) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return

    service = ExportService(session)
    settings = get_settings()
    output_dir = Path(settings.data_dir) / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)

    if callback_data.action == "export_json":
        text = await service.export_json(user.id)
        path = output_dir / f"progress_{user.id}.json"
        path.write_text(text, encoding="utf-8")
        await callback.message.answer_document(FSInputFile(path), caption=t("export_done_json"))
    elif callback_data.action == "export_csv":
        text = await service.export_csv(user.id)
        path = output_dir / f"progress_{user.id}.csv"
        path.write_text(text, encoding="utf-8")
        await callback.message.answer_document(FSInputFile(path), caption=t("export_done_csv"))
    else:
        path = output_dir / f"progress_{user.id}.apkg"
        await service.export_apkg(user.id, path)
        await callback.message.answer_document(FSInputFile(path), caption=t("export_done_apkg"))
    await callback.answer()


@router.callback_query(ProgressCallback.filter(F.action == "reset"))
async def reset_progress_ask(callback: CallbackQuery, session, t) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    await edit_or_send(callback.message, t("progress_reset_ask"), reply_markup=reset_confirm_keyboard(t))
    await callback.answer()


@router.callback_query(ProgressCallback.filter(F.action == "reset_confirm"))
async def reset_progress_confirm(callback: CallbackQuery, session, t) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return

    cards = await CardRepository(session).reset_progress(user.id)
    reviews = await ReviewRepository(session).delete_for_user(user.id)
    await StatisticsRepository(session).delete_for_user(user.id)
    await UserRepository(session).reset_counters(callback.from_user.id)

    await edit_or_send(callback.message, t("progress_reset_done", cards=cards, reviews=reviews))
    await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
    await callback.answer()
