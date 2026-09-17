"""Async engine and session factory."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

# Give SQLite time to wait for a writer instead of failing right away.  Only the
# SQLite driver understands this argument, so it is not passed to other backends.
_CONNECT_ARGS: dict[str, object] = (
    {"timeout": 30} if _settings.database_dsn.startswith("sqlite") else {}
)

engine: AsyncEngine = create_async_engine(
    _settings.database_dsn,
    echo=_settings.sql_echo,
    future=True,
    pool_pre_ping=True,
    connect_args=_CONNECT_ARGS,
)

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # Repositories flush explicitly.  Autoflush would make a pending write break
    # unrelated read queries (that is how a read-only database turned every
    # screen into an error instead of only the writes).
    autoflush=False,
)


async def init_models() -> None:
    """Create working directories, enable WAL and create missing tables."""
    from app.database import models  # noqa: F401  (registers the mappers)
    from app.database.base import Base

    _settings.ensure_directories()
    logger.info("Database file: %s", _settings.db_path)

    async with engine.begin() as connection:
        if _settings.database_dsn.startswith("sqlite"):
            try:
                # WAL keeps readers and writers apart and, more importantly here,
                # stops SQLite from creating and deleting a journal file for every
                # transaction - the file operation that antivirus and file
                # indexers like to interrupt ("attempt to write a readonly
                # database").  The mode is stored in the database itself.
                mode = (await connection.exec_driver_sql("PRAGMA journal_mode=WAL")).scalar()
                logger.info("SQLite journal mode: %s", mode)
            except Exception:  # startup must not fail on this
                logger.warning("Could not switch the database to WAL mode", exc_info=True)
            await connection.exec_driver_sql("PRAGMA busy_timeout=30000")

        await connection.run_sync(Base.metadata.create_all)

        # Fail loudly here instead of on the user's first tap.
        try:
            await connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS _write_probe (id INTEGER)")
            await connection.exec_driver_sql("DROP TABLE _write_probe")
            logger.info("Database is writable")
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Database is NOT writable (%s: %s). Check permissions/antivirus for %s "
                "or point DB_FILE at a different location.",
                type(exc).__name__,
                exc,
                _settings.db_path,
            )


async def dispose_engine() -> None:
    """Close the connection pool, called on shutdown."""
    await engine.dispose()
