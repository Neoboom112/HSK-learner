"""Declarative base and shared column helpers for the ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

# Predictable constraint names keep Alembic diffs stable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Timezone aware "now", used as the Python side column default."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """``DateTime(timezone=True)`` that survives a round trip through SQLite.

    The schema declares every timestamp as timezone aware, but SQLite has no
    timezone support and hands values back naive.  The services do aware
    arithmetic (see ``SRSService.review``), so this type normalises both
    directions: aware values are stored as UTC, stored values come back as UTC
    aware datetimes.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    """Base class for every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdMixin:
    """Autoincrementing integer primary key."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class TimestampMixin:
    """Adds the ``created_at`` / ``updated_at`` bookkeeping columns."""

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )


def metadata_alias(column_name: str) -> property:
    """Expose a JSON column under the Python name ``metadata``.

    ``metadata`` is reserved by the Declarative API because :class:`Base` already
    owns ``Base.metadata`` (the :class:`~sqlalchemy.MetaData` registry).  The
    column is therefore mapped under a private attribute name and re-exposed
    through a property once the mapping is complete, which keeps the public API
    (``card = Card(metadata={...})`` and ``card.metadata``) working as expected.
    """

    def getter(self: Any) -> dict[str, Any]:
        return getattr(self, column_name)

    def setter(self: Any, value: dict[str, Any] | None) -> None:
        setattr(self, column_name, value if value is not None else {})

    return property(getter, setter)


__all__ = ["Base", "IdMixin", "TimestampMixin", "UTCDateTime", "metadata_alias", "utcnow"]
