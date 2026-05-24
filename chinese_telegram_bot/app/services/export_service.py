from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Card, Dictionary
from app.utils.anki import export_apkg


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export_json(self, user_id: int, dictionary_id: int | None = None) -> str:
        stmt = select(Card).where(Card.user_id == user_id)
        if dictionary_id is not None:
            stmt = stmt.where(Card.dictionary_id == dictionary_id)
        result = await self.session.execute(stmt.order_by(Card.id.asc()))
        cards = result.scalars().all()
        payload = [
            {
                "hanzi": card.hanzi,
                "pinyin": card.pinyin,
                "translation": card.translation,
                "audio": card.audio,
                "example_sentence": card.example_sentence,
                "hsk_level": card.hsk_level,
                "tags": card.tags,
                "difficulty": card.difficulty,
                "metadata": card.metadata,
                "ease_factor": card.ease_factor,
                "interval_days": card.interval_days,
                "repetitions": card.repetitions,
                "lapses": card.lapses,
            }
            for card in cards
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    async def export_csv(self, user_id: int, dictionary_id: int | None = None) -> str:
        stmt = select(Card).where(Card.user_id == user_id)
        if dictionary_id is not None:
            stmt = stmt.where(Card.dictionary_id == dictionary_id)
        result = await self.session.execute(stmt.order_by(Card.id.asc()))
        cards = result.scalars().all()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["hanzi", "pinyin", "translation", "audio", "example_sentence", "hsk_level", "tags", "difficulty", "ease_factor", "interval_days", "repetitions", "lapses"])
        for card in cards:
            writer.writerow([
                card.hanzi,
                card.pinyin or "",
                card.translation or "",
                card.audio or "",
                card.example_sentence or "",
                card.hsk_level or "",
                "|".join(card.tags or []),
                card.difficulty,
                card.ease_factor,
                card.interval_days,
                card.repetitions,
                card.lapses,
            ])
        return buffer.getvalue()

    async def export_apkg(self, user_id: int, output_path: Path, dictionary_id: int | None = None) -> Path:
        stmt = select(Card).where(Card.user_id == user_id)
        if dictionary_id is not None:
            stmt = stmt.where(Card.dictionary_id == dictionary_id)
        result = await self.session.execute(stmt.order_by(Card.id.asc()))
        cards = result.scalars().all()
        dict_row = None
        if dictionary_id is not None:
            dict_row = await self.session.get(Dictionary, dictionary_id)
        deck_name = dict_row.name if dict_row else "Chinese Learning Deck"
        export_apkg(
            deck_name=deck_name,
            cards=[
                {
                    "hanzi": card.hanzi,
                    "pinyin": card.pinyin,
                    "translation": card.translation,
                    "example_sentence": card.example_sentence,
                    "audio": card.audio,
                    "hsk_level": card.hsk_level,
                    "tags": card.tags,
                    "ease_factor": card.ease_factor,
                    "interval_days": card.interval_days,
                    "repetitions": card.repetitions,
                    "lapses": card.lapses,
                }
                for card in cards
            ],
            output_path=output_path,
        )
        return output_path
