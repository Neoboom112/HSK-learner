from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import get_settings
from app.services.backup_service import BackupService

router = Router(name=__name__)


@router.message(Command("admin"))
async def admin_panel(message: Message, t) -> None:
    settings = get_settings()
    if message.from_user.id not in settings.admin_id_list:
        return
    backup_path = BackupService().run_backup()
    await message.answer(
        f"{t('admin_title')}\n"
        f"{t('admin_backup_ready')}: <code>{backup_path.name}</code>"
    )
