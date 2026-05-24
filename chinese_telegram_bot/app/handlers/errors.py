from __future__ import annotations

from aiogram import Router
from aiogram.types import ErrorEvent

router = Router(name=__name__)


@router.errors()
async def on_error(event: ErrorEvent, t) -> bool:
    if event.update and getattr(event.update, "message", None):
        await event.update.message.answer(t("error_generic"))
    return True
