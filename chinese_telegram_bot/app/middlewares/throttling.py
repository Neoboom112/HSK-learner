from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        now = monotonic()
        last = self.last_seen.get(user.id, 0.0)
        if now - last < self.interval:
            return
        self.last_seen[user.id] = now
        return await handler(event, data)
