from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import genanki

from app.models.schemas import CardDraft


def parse_apkg(apkg_path: Path) -> tuple[str, list[CardDraft]]:
    with zipfile.ZipFile(apkg_path, "r") as archive:
        collection_name = "Anki deck"
        collection_data = archive.read("collection.anki2")
        temp_db = apkg_path.with_suffix(".anki2.tmp")
        temp_db.write_bytes(collection_data)
        try:
            conn = sqlite3.connect(temp_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            deck_name = collection_name
            cards: list[CardDraft] = []

            deck_rows = cursor.execute("SELECT decks FROM col LIMIT 1").fetchone()
            if deck_rows:
                decks = json.loads(deck_rows[0])
                if decks:
                    first_deck = next(iter(decks.values()))
                    deck_name = first_deck.get("name") or collection_name

            model_rows = cursor.execute("SELECT models FROM col LIMIT 1").fetchone()
            model_fields: list[str] = []
            if model_rows:
                models = json.loads(model_rows[0])
                if models:
                    first_model = next(iter(models.values()))
                    model_fields = [field["name"].lower() for field in first_model.get("flds", [])]

            note_rows = cursor.execute("SELECT flds, tags, sfld FROM notes LIMIT 100000").fetchall()
            for row in note_rows:
                fields = row["flds"].split("\x1f")
                values = {model_fields[i] if i < len(model_fields) else f"field_{i}": fields[i] for i in range(len(fields))}
                hanzi = values.get("hanzi") or values.get("front") or values.get("field_0") or ""
                pinyin = values.get("pinyin") or values.get("field_1")
                translation = values.get("translation") or values.get("meaning") or values.get("back") or values.get("field_2")
                example = values.get("example") or values.get("sentence") or values.get("field_3")
                audio = values.get("audio") or values.get("field_4")
                hsk = None
                raw_hsk = values.get("hsk") or values.get("level") or values.get("field_5")
                if raw_hsk:
                    try:
                        hsk = int(str(raw_hsk).strip().replace("HSK", ""))
                    except ValueError:
                        hsk = None
                tags = [tag for tag in row["tags"].split() if tag] if row["tags"] else []
                cards.append(
                    CardDraft(
                        hanzi=hanzi,
                        pinyin=pinyin,
                        translation=translation,
                        example_sentence=example,
                        audio=audio,
                        hsk_level=hsk,
                        tags=tags,
                        metadata={"source": "apkg", "ankisfld": row["sfld"]},
                    )
                )
            return deck_name, cards
        finally:
            conn.close()
            if temp_db.exists():
                temp_db.unlink(missing_ok=True)


def export_apkg(deck_name: str, cards: list[dict[str, Any]], output_path: Path) -> Path:
    model = genanki.Model(
        1607392319,
        "Chinese Learning Model",
        fields=[
            {"name": "Hanzi"},
            {"name": "Pinyin"},
            {"name": "Translation"},
            {"name": "Example"},
            {"name": "Audio"},
            {"name": "HSK"},
            {"name": "Tags"},
            {"name": "Ease"},
            {"name": "Interval"},
            {"name": "Reps"},
            {"name": "Lapses"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Hanzi}}<br><small>{{Pinyin}}</small>",
                "afmt": "{{FrontSide}}<hr id='answer'>{{Translation}}<br>{{Example}}",
            }
        ],
    )
    deck = genanki.Deck(2059400110, deck_name)
    for card in cards:
        note = genanki.Note(
            model=model,
            fields=[
                card.get("hanzi", ""),
                card.get("pinyin", ""),
                card.get("translation", ""),
                card.get("example_sentence", ""),
                card.get("audio", ""),
                str(card.get("hsk_level") or ""),
                " ".join(card.get("tags") or []),
                str(card.get("ease_factor", "")),
                str(card.get("interval_days", "")),
                str(card.get("repetitions", "")),
                str(card.get("lapses", "")),
            ],
            tags=card.get("tags") or [],
        )
        deck.add_note(note)
    genanki.Package(deck).write_to_file(output_path)
    return output_path
