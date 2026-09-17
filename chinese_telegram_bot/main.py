"""Entry point of the Chinese Learning Telegram Bot.

Run with ``python main.py`` after installing ``requirements.txt`` and creating a
``.env`` file (see ``.env.example``).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot_profile import apply_bot_profile
from app.config import Settings, get_settings
from app.database.session import async_session, dispose_engine, init_models
from app.handlers import get_routers
from app.i18n import get_localizer
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.i18n import LocaleMiddleware
from app.middlewares.outbox import OutboxMiddleware
from app.middlewares.throttling import ThrottleMiddleware
from app.repositories.users import UserRepository
from app.schedulers.backup_scheduler import BackupScheduler
from app.schedulers.review_scheduler import ReviewScheduler
from app.services.dictionary_service import DictionaryBootstrapService

logger = logging.getLogger(__name__)


class LocaleFallbackMiddleware(LocaleMiddleware):
    """Keeps ``t`` available for error handlers.

    Error events are dispatched through their own observer.  When the exception
    happened after :class:`LocaleMiddleware` did its job the localiser is already
    part of the event context and must be re-used.  Otherwise the language is
    looked up again from the database, so a user never gets an error message in
    a language they did not choose.
    """

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        if data.get("t") is not None:
            return await handler(event, data)
        data = dict(data)
        data["locale"] = await self._resolve_locale(event)
        data["t"] = get_localizer(data["locale"]).t
        return await handler(event, data)

    @staticmethod
    async def _resolve_locale(event: Any) -> str:
        settings = get_settings()
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            update = getattr(event, "update", None)
            from_user = getattr(update, "from_user", None)
        if from_user is None:
            return settings.default_locale
        try:
            async with async_session() as session:
                user = await UserRepository(session).get_by_telegram_id(from_user.id)
        except Exception:  # the database may be the broken part
            logger.warning("Could not resolve the locale for the error message", exc_info=True)
            return settings.default_locale
        return user.language if user is not None and user.language else settings.default_locale


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Log to the console and, when possible, to a rotating file.

    The file survives restarts and is what to send when something misbehaves.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(
                RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            )
        except OSError:
            pass
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )


def create_bot(settings: Settings) -> Bot:
    """Build the bot instance with HTML parsing enabled by default."""
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # Replies stay queued until the update's transaction is committed, so a
    # replayed update never sends its messages twice.
    bot.session.middleware(OutboxMiddleware())
    return bot


# Observers whose events carry ``from_user``; the shipped middlewares read the
# user straight off the event object, so they cannot live on the ``update``
# observer (where the event is an ``Update`` wrapper without that attribute).
USER_EVENT_OBSERVERS = ("message", "callback_query")


def create_dispatcher(settings: Settings) -> Dispatcher:
    """Wire middlewares and routers into a ready to run dispatcher."""
    dispatcher = Dispatcher(storage=MemoryStorage())

    # Outer middlewares run in registration order: throttle first (it may drop
    # the event), then the database session, then the localiser that needs it.
    for name in USER_EVENT_OBSERVERS:
        observer = dispatcher.observers[name]
        observer.outer_middleware(ThrottleMiddleware(settings.throttle_interval))
        observer.outer_middleware(DbSessionMiddleware())
        observer.outer_middleware(LocaleMiddleware())

    # Error handlers live in their own observer, so they need their own fallback.
    dispatcher.errors.outer_middleware(LocaleFallbackMiddleware())

    for router in get_routers():
        dispatcher.include_router(router)

    return dispatcher


async def prepare_storage() -> None:
    """Create the database schema and install the bundled starter deck."""
    await init_models()
    await DictionaryBootstrapService().ensure_seed_dictionary()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_path)

    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN is empty. Copy .env.example to .env and set the token issued by @BotFather."
        )

    await prepare_storage()

    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings)

    # Descriptions and the command menu of the bot profile.
    await apply_bot_profile(bot, settings)

    review_scheduler = ReviewScheduler(bot)
    backup_scheduler = BackupScheduler(bot)
    await review_scheduler.start()
    await backup_scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot is polling")
        await dispatcher.start_polling(bot)
    finally:
        await review_scheduler.stop()
        await backup_scheduler.stop()
        await bot.session.close()
        await dispose_engine()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
