from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent
from sqlalchemy.exc import SQLAlchemyError

router = Router(name=__name__)
logger = logging.getLogger(__name__)

# Telegram rejects an edit that would not change anything. Users produce this by
# tapping the same inline button twice, and it is not worth an error screen.
IGNORED_BAD_REQUESTS = ("message is not modified",)


@router.errors()
async def on_error(event: ErrorEvent, t) -> bool:
    exception = event.exception
    update_id = getattr(event.update, "update_id", "?")
    is_database = isinstance(exception, SQLAlchemyError)

    # Always record the cause: a handled error event counts as success for the
    # dispatcher, so without this the reason would be lost.  Database hiccups are
    # transient by nature, so they are logged without a full traceback.
    if is_database:
        logger.warning("Update %s failed: %s: %s", update_id, type(exception).__name__, exception)
    else:
        logger.error(
            "Update %s failed: %s: %s",
            update_id,
            type(exception).__name__,
            exception,
            exc_info=exception,
        )

    if isinstance(exception, TelegramBadRequest) and any(
        fragment in str(exception) for fragment in IGNORED_BAD_REQUESTS
    ):
        logger.info("Ignored no-op edit for update %s", update_id)
        return True

    # A failing button press has no chat message of its own: take the one from the
    # callback query and stop its spinner, otherwise the user sees nothing at all.
    update = event.update
    callback = getattr(update, "callback_query", None)
    message = getattr(update, "message", None) or getattr(callback, "message", None)

    if callback is not None:
        try:
            await callback.answer()
        except Exception:  # noqa: BLE001 - reporting the error must not fail
            logger.debug("Could not answer the callback while handling an error")

    if message is None:
        return True

    if is_database:
        await message.answer(t("error_database"))
    else:
        await message.answer(t("error_generic"))
    return True
