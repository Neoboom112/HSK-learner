"""Queue user visible replies until the database transaction is committed.

A replayed update would otherwise send every message again; holding the replies
back makes the retry invisible.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageCaption,
    EditMessageReplyMarkup,
    EditMessageText,
    SendChatAction,
    SendDocument,
    SendMessage,
    SendPhoto,
)

logger = logging.getLogger(__name__)

# Only user visible replies are deferred.  Everything else (GetFile, downloads,
# profile updates, ...) keeps its immediate semantics because handlers use the
# result of those calls.
BUFFERED_METHODS = (
    SendMessage,
    SendPhoto,
    SendDocument,
    EditMessageText,
    EditMessageCaption,
    EditMessageReplyMarkup,
    AnswerCallbackQuery,
    SendChatAction,
)

_Pending = list[tuple[Any, Any, Any, Any]]
_pending: ContextVar[_Pending | None] = ContextVar("outbox", default=None)


class OutboxMiddleware:
    """aiogram request middleware: hold replies until the outbox is flushed."""

    async def __call__(self, make_request, bot, method, timeout=None):
        pending = _pending.get()
        if pending is None or not isinstance(method, BUFFERED_METHODS):
            return await make_request(bot, method, timeout=timeout)
        pending.append((make_request, bot, method, timeout))
        return True


def open_outbox() -> None:
    """Start collecting replies for the current event."""
    _pending.set([])


def close_outbox() -> _Pending:
    """Stop collecting and return what was queued."""
    entries = _pending.get() or []
    _pending.set(None)
    return entries


async def flush_outbox(entries: _Pending) -> None:
    """Send the queued replies, in the order the handler produced them."""
    for make_request, bot, method, timeout in entries:
        try:
            await make_request(bot, method, timeout=timeout)
        except Exception:  # a failed reply must not kill the bot
            logger.exception("Could not deliver %s after commit", type(method).__name__)
