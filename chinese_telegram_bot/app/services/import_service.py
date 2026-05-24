from __future__ import annotations

import csv
import io
import json
import tempfile
from pathlib import Path

from app.models.schemas import CardDraft
from app.utils.anki import parse_apkg
from app.utils.validators import infer_hsk_level, parse_tags


class DictionaryImportService:
    def parse_bytes(self, filename: str, content: bytes) -> list[CardDraft]:
        ext = Path(filename).suffix.lower()
        if ext == ".csv":
            return self._parse_csv(content)
        if ext == ".json":
            return self._parse_json(content)
        if ext == ".txt":
            return self._parse_txt(content)
        if ext == ".apkg":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".apkg") as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(content)
            try:
                _, cards = parse_apkg(tmp_path)
                return cards
            finally:
                tmp_path.unlink(missing_ok=True)
        raise ValueError(f"Unsupported file format: {ext}")

    def _parse_csv(self, content: bytes) -> list[CardDraft]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        items: list[CardDraft] = []
        for row in reader:
            items.append(self._row_to_card(row))
        return items

    def _parse_json(self, content: bytes) -> list[CardDraft]:
        payload = json.loads(content.decode("utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("cards", payload.get("items", []))
        items: list[CardDraft] = []
        for row in payload:
            items.append(self._row_to_card(row))
        return items

    def _parse_txt(self, content: bytes) -> list[CardDraft]:
        text = content.decode("utf-8-sig")
        items: list[CardDraft] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.replace("\t", "|").split("|")]
            while len(parts) < 7:
                parts.append("")
            row = {
                "hanzi": parts[0],
                "pinyin": parts[1],
                "translation": parts[2],
                "audio": parts[3],
                "example_sentence": parts[4],
                "hsk_level": parts[5],
                "tags": parts[6],
            }
            items.append(self._row_to_card(row))
        return items

    def _row_to_card(self, row: dict) -> CardDraft:
        hanzi = str(row.get("hanzi") or row.get("front") or row.get("word") or row.get("词") or "").strip()
        if not hanzi:
            raise ValueError("Every card must have hanzi")
        pinyin = str(row.get("pinyin") or row.get("py") or row.get("pronunciation") or "").strip() or None
        translation = str(row.get("translation") or row.get("meaning") or row.get("back") or row.get("definition") or "").strip() or None
        audio = str(row.get("audio") or row.get("audio_url") or row.get("sound") or "").strip() or None
        example_sentence = str(row.get("example_sentence") or row.get("example") or row.get("sentence") or "").strip() or None
        hsk_level = infer_hsk_level(str(row.get("hsk_level") or row.get("hsk") or row.get("level") or ""))
        tags = parse_tags(str(row.get("tags") or row.get("tag") or ""))
        difficulty_raw = row.get("difficulty") or row.get("score") or 1
        try:
            difficulty = int(difficulty_raw)
        except Exception:
            difficulty = 1
        metadata = {
            k: v for k, v in row.items()
            if k not in {"hanzi", "front", "word", "词", "pinyin", "py", "pronunciation", "translation", "meaning", "back", "definition", "audio", "audio_url", "sound", "example_sentence", "example", "sentence", "hsk_level", "hsk", "level", "tags", "tag", "difficulty", "score"}
        }
        return CardDraft(
            hanzi=hanzi,
            pinyin=pinyin,
            translation=translation,
            audio=audio,
            example_sentence=example_sentence,
            hsk_level=hsk_level,
            tags=tags,
            difficulty=difficulty,
            metadata=metadata,
        )
