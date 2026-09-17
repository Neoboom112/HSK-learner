from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.dispatcher.middlewares.base import BaseMiddleware

from app.config import get_settings
from app.i18n import get_localizer
from app.repositories.users import UserRepository


class LocaleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        settings = get_settings()
        session = data.get("session")
        locale = settings.default_locale
        if session is not None and getattr(event, "from_user", None):
            user = await UserRepository(session).get_by_telegram_id(event.from_user.id)
            if user is not None:
                locale = user.language or locale
        data["locale"] = locale
        data["t"] = get_localizer(locale).t
        return await handler(event, data)
