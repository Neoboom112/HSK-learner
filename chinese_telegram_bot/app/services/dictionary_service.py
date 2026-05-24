from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models import Card, Dictionary, User
from app.models.enums import DictionarySource
from app.models.schemas import CardDraft
from app.repositories.cards import CardRepository
from app.repositories.dictionaries import DictionaryRepository
from app.services.import_service import DictionaryImportService


class DictionaryBootstrapService:
    async def ensure_seed_dictionary(self) -> None:
        from app.database.session import async_session

        settings = get_settings()
        seed_path = Path(settings.data_dir) / "dictionaries" / "basic_hsk1.json"
        if not seed_path.exists():
            return
        async with async_session() as session:
            repo = DictionaryRepository(session)
            result = await session.execute(
                select(Dictionary).where(Dictionary.is_system.is_(True), Dictionary.name == "HSK 1 Basics")
            )
            if result.scalar_one_or_none():
                return
            dictionary = await repo.create(
                owner_user_id=None,
                name="HSK 1 Basics",
                source_type=DictionarySource.SYSTEM.value,
                language="zh",
                is_system=True,
                description="Preinstalled starter deck for quick onboarding.",
                meta={"level": "HSK1", "seed": True},
            )
            data = json.loads(seed_path.read_text(encoding="utf-8"))
            cards = [CardDraft.model_validate(item) for item in data]
            user = User(telegram_id=0, language="en", username="system", full_name="system")
            session.add(user)
            await session.flush()
            await CardRepository(session).bulk_upsert(user_id=user.id, dictionary_id=dictionary.id, items=cards)
            await session.commit()


class DictionaryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DictionaryRepository(session)
        self.importer = DictionaryImportService()
        self.cards = CardRepository(session)

    async def list_for_user(self, user_id: int) -> list[Dictionary]:
        return await self.repo.list_available_for_user(user_id)

    async def create_user_dictionary(self, user_id: int, name: str, source_type: str, language: str = "zh") -> Dictionary:
        return await self.repo.create(owner_user_id=user_id, name=name, source_type=source_type, language=language)

    async def clone_system_dictionary(self, user_id: int, dictionary: Dictionary) -> tuple[int, int]:
        if not dictionary.is_system:
            return 0, 0
        system_user = await self.session.execute(select(User).where(User.telegram_id == 0))
        system = system_user.scalar_one_or_none()
        if system is None:
            return 0, 0
        result = await self.session.execute(select(Card).where(Card.user_id == system.id, Card.dictionary_id == dictionary.id))
        system_cards = result.scalars().all()
        drafts = [
            CardDraft(
                hanzi=card.hanzi,
                pinyin=card.pinyin,
                translation=card.translation,
                audio=card.audio,
                example_sentence=card.example_sentence,
                hsk_level=card.hsk_level,
                tags=list(card.tags or []),
                difficulty=card.difficulty,
                metadata=dict(card.metadata or {}),
            )
            for card in system_cards
        ]
        return await self.cards.bulk_upsert(user_id, dictionary.id, drafts)

    async def import_file(
        self,
        user: User,
        filename: str,
        payload: bytes,
        dictionary_name: str | None = None,
        language: str = "zh",
        source_type: str | None = None,
    ) -> tuple[Dictionary, int, int]:
        cards = self.importer.parse_bytes(filename, payload)
        if not cards:
            raise ValueError("No valid cards found")
        dictionary = await self.repo.create(
            owner_user_id=user.id,
            name=dictionary_name or Path(filename).stem,
            source_type=source_type or Path(filename).suffix.lstrip("."),
            language=language,
            is_system=False,
            meta={"original_filename": filename, "imported_count": len(cards)},
        )
        imported, duplicates = await self.cards.bulk_upsert(user.id, dictionary.id, cards)
        return dictionary, imported, duplicates
