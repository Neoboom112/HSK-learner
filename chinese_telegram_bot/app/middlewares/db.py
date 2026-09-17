from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from sqlalchemy.exc import OperationalError

from app.database.session import async_session
from app.middlewares.outbox import close_outbox, flush_outbox, open_outbox

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """One session per update, replaying it when the write fails transiently.

    SQLite on Windows occasionally refuses a write ("attempt to write a readonly
    database") while antivirus or a file watcher holds the journal file.  Nothing
    is committed in that case, so the update can simply run again; the outbox
    drops the replies of the failed attempt to keep that invisible.
    """

    def __init__(self, attempts: int = 3, delay: float = 0.4) -> None:
        self.attempts = max(1, attempts)
        self.delay = delay

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        last_error: Exception | None = None

        for attempt in range(1, self.attempts + 1):
            open_outbox()
            try:
                async with async_session() as session:
                    data["session"] = session
                    result = await handler(event, data)
                    await session.commit()
            except OperationalError as exc:
                # Nothing was committed: throw the queued replies away and retry.
                close_outbox()
                last_error = exc
                logger.warning(
                    "Database write failed (attempt %s/%s): %s: %s",
                    attempt,
                    self.attempts,
                    type(exc).__name__,
                    exc,
                )
                if attempt < self.attempts:
                    await asyncio.sleep(self.delay * attempt)
                continue
            except Exception:
                # Some other failure: keep what the handler already produced and
                # let the error handler add its message on top of it.
                await flush_outbox(close_outbox())
                raise

            await flush_outbox(close_outbox())
            return result

        assert last_error is not None
        raise last_error
