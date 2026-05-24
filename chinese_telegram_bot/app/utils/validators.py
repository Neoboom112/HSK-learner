from __future__ import annotations

from pathlib import Path

from app.models.schemas import CardDraft


def normalize_text(value: str | None) -> str:
    return (value or "").strip()


def fingerprint_card(hanzi: str, pinyin: str | None, translation: str | None) -> str:
    raw = " | ".join([normalize_text(hanzi), normalize_text(pinyin), normalize_text(translation)]).lower()
    return raw.replace("  ", " ").strip()


def validate_dictionary_name(name: str) -> str:
    name = normalize_text(name)
    if not name:
        raise ValueError("Dictionary name is empty")
    if len(name) > 120:
        raise ValueError("Dictionary name is too long")
    return name


def infer_hsk_level(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = normalize_text(value).lower().replace("hsk", "").replace("level", "").strip()
    try:
        level = int(cleaned)
    except ValueError:
        return None
    return level if 1 <= level <= 6 else None


def parse_tags(value: str | None) -> list[str]:
    raw = normalize_text(value)
    if not raw:
        return []
    separators = ["|", ";", ",", "/"]
    for separator in separators:
        if separator in raw:
            return [item.strip() for item in raw.split(separator) if item.strip()]
    return [raw]


def safe_extension(filename: str) -> str:
    return Path(filename).suffix.lower()
