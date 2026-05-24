from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Dictionary


class DictionaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_system(self) -> list[Dictionary]:
        result = await self.session.execute(select(Dictionary).where(Dictionary.is_system.is_(True)).order_by(Dictionary.name))
        return list(result.scalars().all())

    async def list_user(self, user_id: int) -> list[Dictionary]:
        result = await self.session.execute(
            select(Dictionary)
            .where(Dictionary.owner_user_id == user_id)
            .order_by(Dictionary.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_available_for_user(self, user_id: int) -> list[Dictionary]:
        result = await self.session.execute(
            select(Dictionary)
            .where((Dictionary.is_system.is_(True)) | (Dictionary.owner_user_id == user_id))
            .order_by(Dictionary.is_system.desc(), Dictionary.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, dictionary_id: int) -> Dictionary | None:
        result = await self.session.execute(select(Dictionary).where(Dictionary.id == dictionary_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        owner_user_id: int | None,
        name: str,
        source_type: str,
        language: str = "zh",
        is_system: bool = False,
        description: str | None = None,
        meta: dict | None = None,
    ) -> Dictionary:
        dictionary = Dictionary(
            owner_user_id=owner_user_id,
            name=name,
            source_type=source_type,
            language=language,
            is_system=is_system,
            description=description,
            meta=meta or {},
        )
        self.session.add(dictionary)
        await self.session.flush()
        return dictionary

    async def set_active(self, user, dictionary_id: int | None) -> None:
        user.active_dictionary_id = dictionary_id
        await self.session.flush()
