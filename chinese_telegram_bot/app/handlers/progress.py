from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.callbacks import ProgressCallback
from app.config import get_settings
from app.keyboards.common import main_menu_keyboard
from app.keyboards.progress import progress_keyboard
from app.repositories.users import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService
from app.utils.charts import line_chart

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


@router.message(F.text)
async def progress_chart(message: Message, session, t) -> None:
    if message.text != t("menu_progress"):
        return
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(t("need_start"))
        return
    analytics = await AnalyticsService(session).summary(user.id)
    monthly = analytics.monthly_progress or [{"date": "n/a", "reviews": 0}]
    labels = [row["date"][-5:] if isinstance(row["date"], str) else str(row["date"]) for row in monthly[-14:]]
    values = [row["reviews"] for row in monthly[-14:]]
    chart = line_chart(labels, values, t("progress_chart_title"), t("progress_reviews"))
    await message.answer_photo(FSInputFile(chart), caption=t("progress_chart_caption"), reply_markup=progress_keyboard(t))
