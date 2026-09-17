from __future__ import annotations

import html
import io
import json
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import genanki

from app.models.schemas import CardDraft

# Anki has shipped several package layouts:
#   collection.anki2   - plain sqlite, legacy clients
#   collection.anki21  - plain sqlite, v2 scheduler (still plain!)
#   collection.anki21b - zstd compressed sqlite, Anki 2.1.50+
# The payload is sniffed instead of trusting the member name.
COLLECTION_MEMBERS = ("collection.anki21b", "collection.anki21", "collection.anki2")
SQLITE_MAGIC = b"SQLite format 3\x00"

_SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

# Field names seen in the wild, matched case insensitively for Latin ones.
HANZI_KEYS = (
    "hanzi", "simplified", "traditional", "front", "word", "character", "expression", "term",
    "生词", "词", "词语", "单词", "汉字", "简体", "繁体", "中文", "字",
    "слово", "иероглиф",
)
PINYIN_KEYS = ("pinyin", "py", "pronunciation", "reading", "romanization", "拼音", "读音", "пиньинь", "чтение")
TRANSLATION_KEYS = (
    "translation", "meaning", "english", "russian", "back", "definition", "answer", "gloss",
    "翻译", "意思", "释义", "解释", "俄语", "英语", "英文",
    "перевод", "значение",
)
EXAMPLE_KEYS = ("example", "example_sentence", "sentence", "usage", "例句", "例子", "句子", "пример")
AUDIO_KEYS = ("audio", "audio_url", "sound", "audio_file", "音频", "声音", "аудио")
HSK_KEYS = ("hsk", "hsk_level", "level", "级别", "等级", "уровень")


def _decompress_zstd(payload: bytes) -> bytes:
    try:
        import zstandard
    except ImportError:  # pragma: no cover - optional dependency
        try:  # Python 3.14+
            from compression import zstd as zstandard  # type: ignore[no-redef]
        except ImportError as exc:
            raise ValueError(
                "This package was exported by a recent Anki version (zstd compressed). "
                "Install 'zstandard' or re-export the deck with 'Support older Anki versions'."
            ) from exc

    try:
        reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(payload))
        try:
            return reader.read()
        finally:
            reader.close()
    except Exception as exc:  # noqa: BLE001 - zstandard raises its own error type
        raise ValueError(f"Could not unpack the compressed collection: {exc}") from exc


def _as_sqlite(payload: bytes) -> bytes:
    """Return plain sqlite bytes: packages store it as is or zstd compressed."""
    if payload.startswith(SQLITE_MAGIC):
        return payload
    return _decompress_zstd(payload)


def _extract_collection(archive: zipfile.ZipFile, workdir: Path) -> Path:
    """Write the collection database of ``archive`` into ``workdir``."""
    names = set(archive.namelist())
    candidates = [member for member in COLLECTION_MEMBERS if member in names]
    if not candidates:
        raise ValueError(
            "This file is not an Anki package: no collection database inside. "
            "Export the deck from Anki with 'Anki deck package (*.apkg)'."
        )

    problems: list[str] = []
    for member in candidates:
        try:
            payload = _as_sqlite(archive.read(member))
        except ValueError as exc:
            problems.append(f"{member}: {exc}")
            continue
        target = workdir / member
        target.write_bytes(payload)
        return target

    raise ValueError("Could not read the Anki collection inside this package (" + "; ".join(problems) + ")")


def _clean(value: str | None) -> str | None:
    """Strip Anki markup (html, media references, entities) from a field."""
    if not value:
        return None
    text = _SOUND_RE.sub(" ", value)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text or None


def _audio_reference(value: str | None) -> str | None:
    match = _SOUND_RE.search(value or "")
    return match.group(1).strip() or None if match else None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("hsk", "").replace("level", "").strip()
    try:
        return int(text)
    except ValueError:
        return None


def _has_table(cursor: sqlite3.Cursor, table: str) -> bool:
    try:
        row = cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
    except sqlite3.Error:
        return False
    return row is not None


def _columns(cursor: sqlite3.Cursor, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in cursor.execute(f'PRAGMA table_info("{table}")')}
    except sqlite3.Error:
        return set()


def _models(cursor: sqlite3.Cursor) -> dict[int, tuple[str, list[str]]]:
    """Map model id -> (model name, field names).

    Old collections keep the models as JSON in ``col.models``, newer ones use the
    normalized ``notetypes``/``fields`` tables.
    """
    models: dict[int, tuple[str, list[str]]] = {}
    try:
        row = cursor.execute("SELECT models FROM col LIMIT 1").fetchone()
    except sqlite3.Error:
        row = None
    if row and row[0]:
        try:
            payload = json.loads(row[0])
        except (TypeError, ValueError):
            payload = {}
        for model_id, model in payload.items():
            if not isinstance(model, dict):
                continue
            fields = [str(f.get("name", "")) for f in model.get("flds", []) if isinstance(f, dict)]
            models[int(model_id)] = (str(model.get("name") or ""), fields)

    if models:
        return models

    if _has_table(cursor, "notetypes") and _has_table(cursor, "fields"):
        names: dict[int, str] = {}
        for row in cursor.execute("SELECT id, name FROM notetypes"):
            names[int(row[0])] = str(row[1] or "")
        fields_by_model: dict[int, list[tuple[int, str]]] = {}
        for row in cursor.execute("SELECT ntid, ord, name FROM fields"):
            fields_by_model.setdefault(int(row[0]), []).append((int(row[1] or 0), str(row[2] or "")))
        for model_id, pairs in fields_by_model.items():
            ordered = [name for _ord, name in sorted(pairs)]
            models[model_id] = (names.get(model_id, ""), ordered)
    return models


def _decks(cursor: sqlite3.Cursor) -> dict[int, str]:
    """Map deck id -> deck name (JSON in ``col`` or the modern ``decks`` table)."""
    decks: dict[int, str] = {}
    try:
        row = cursor.execute("SELECT decks FROM col LIMIT 1").fetchone()
    except sqlite3.Error:
        row = None
    if row and row[0]:
        try:
            payload = json.loads(row[0])
        except (TypeError, ValueError):
            payload = {}
        for deck_id, deck in payload.items():
            if isinstance(deck, dict):
                decks[int(deck_id)] = str(deck.get("name") or "")

    if decks:
        return decks

    if _has_table(cursor, "decks"):
        try:
            for row in cursor.execute("SELECT id, name FROM decks"):
                decks[int(row[0])] = str(row[1] or "")
        except sqlite3.Error:
            pass
    return decks


def _primary_deck_name(cursor: sqlite3.Cursor, decks: dict[int, str]) -> str:
    """Name of the deck that holds most of the cards (skipping Anki's 'Default')."""
    try:
        rows = cursor.execute("SELECT did, COUNT(*) AS n FROM cards GROUP BY did ORDER BY n DESC").fetchall()
    except sqlite3.Error:
        rows = []
    for deck_id, _count in rows:
        name = decks.get(int(deck_id))
        if name and name != "Default":
            return name
    for name in decks.values():
        if name and name != "Default":
            return name
    return "Anki deck"


def _pick(values: dict[str, str], keys: tuple[str, ...]) -> str | None:
    """First field whose (lower cased) name matches one of ``keys``."""
    for key in keys:
        for name, value in values.items():
            if name.lower() == key:
                return value
    return None


def _note_to_draft(
    values: dict[str, str],
    positional: dict[str, str],
    tags: list[str],
    deck_name: str,
    model_name: str,
    sort_field: str | None,
) -> CardDraft | None:
    # Named match first, then the usual field order of a vocabulary note.
    hanzi = _clean(_pick(values, HANZI_KEYS) or positional.get("field_0"))
    if not hanzi:
        return None

    pinyin = _clean(_pick(values, PINYIN_KEYS) or positional.get("field_1"))
    translation = _clean(_pick(values, TRANSLATION_KEYS) or positional.get("field_2"))
    example = _clean(_pick(values, EXAMPLE_KEYS) or positional.get("field_3"))
    hsk_level = _as_int(_pick(values, HSK_KEYS))
    audio = (
        _audio_reference(" ".join(values.values()))
        or _clean(_pick(values, AUDIO_KEYS))
    )

    metadata: dict[str, Any] = {"source": "apkg"}
    if deck_name:
        metadata["deck"] = deck_name
    if model_name:
        metadata["model"] = model_name
    if sort_field:
        metadata["sfld"] = sort_field

    return CardDraft(
        hanzi=hanzi,
        pinyin=pinyin,
        translation=translation,
        audio=audio,
        example_sentence=example,
        hsk_level=hsk_level,
        tags=tags,
        metadata=metadata,
    )


def _read_collection(db_path: Path) -> tuple[str, list[CardDraft]]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.cursor()
        models = _models(cursor)
        decks = _decks(cursor)
        deck_name = _primary_deck_name(cursor, decks)

        columns = _columns(cursor, "notes")
        if "flds" not in columns:
            raise ValueError("The Anki collection has no usable notes table.")

        # Newer schemas keep note tags in a separate table.
        tags_by_note: dict[int, list[str]] = {}
        if "tags" not in columns and _has_table(cursor, "tags"):
            try:
                for note_id, tag in cursor.execute("SELECT ntid, tag FROM tags"):
                    tags_by_note.setdefault(int(note_id), []).append(str(tag))
            except sqlite3.Error:
                tags_by_note = {}

        selected = [name for name in ("id", "mid", "flds", "tags", "sfld") if name in columns]
        cards: list[CardDraft] = []
        for row in cursor.execute(f"SELECT {', '.join(selected)} FROM notes"):
            fields = (row["flds"] or "").split("\x1f")
            model_name, field_names = models.get(int(row["mid"] or 0), ("", []))

            positional = {f"field_{index}": value for index, value in enumerate(fields)}
            values: dict[str, str] = {}
            for index, name in enumerate(field_names):
                if index < len(fields) and name:
                    values[name] = fields[index]

            if "tags" in columns:
                tags = [tag for tag in (row["tags"] or "").split() if tag]
            else:
                tags = tags_by_note.get(int(row["id"] or 0), [])

            draft = _note_to_draft(
                values,
                positional,
                tags,
                deck_name,
                model_name,
                row["sfld"] if "sfld" in columns else None,
            )
            if draft is not None:
                cards.append(draft)
        return deck_name, cards
    finally:
        connection.close()


def parse_apkg(apkg_path: Path) -> tuple[str, list[CardDraft]]:
    """Read an ``.apkg`` package and return ``(deck name, cards)``.

    Raises :class:`ValueError` with a user facing message when the file cannot be
    used, whatever the subformat of the package is.
    """
    try:
        with zipfile.ZipFile(apkg_path, "r") as archive, tempfile.TemporaryDirectory(prefix="apkg_") as workdir:
            db_path = _extract_collection(archive, Path(workdir))
            return _read_collection(db_path)
    except zipfile.BadZipFile as exc:
        raise ValueError("This file is not an Anki package: it is not a valid .apkg archive.") from exc
    except sqlite3.Error as exc:
        raise ValueError(f"Could not read the Anki collection database: {exc}") from exc


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
