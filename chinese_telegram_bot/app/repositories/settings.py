from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Setting


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int, key: str, default: str | None = None) -> str | None:
        result = await self.session.execute(
            select(Setting).where(Setting.user_id == user_id, Setting.key == key)
        )
        row = result.scalar_one_or_none()
        return row.value if row else default

    async def set(self, user_id: int, key: str, value: str) -> None:
        result = await self.session.execute(
            select(Setting).where(Setting.user_id == user_id, Setting.key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = Setting(user_id=user_id, key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
        await self.session.flush()
