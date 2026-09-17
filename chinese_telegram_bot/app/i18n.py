"""JSON backed localisation: ``locales/<code>.json`` plus the ``t()`` helper."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from app.config import get_settings

FALLBACK_LOCALE = "en"


class Localizer:
    """Message catalogue for a single locale with a fallback catalogue."""

    def __init__(
        self,
        locale: str,
        messages: dict[str, str],
        fallback: dict[str, str] | None = None,
    ) -> None:
        self.locale = locale
        self._messages = messages
        self._fallback = fallback or {}

    def get(self, key: str, default: str | None = None) -> str:
        """Return a raw template, falling back to English and finally the key."""
        value = self._messages.get(key)
        if value is None:
            value = self._fallback.get(key)
        if value is None:
            return key if default is None else default
        return value

    def t(self, key: str, **kwargs: object) -> str:
        """Render ``key`` with optional ``str.format`` placeholders."""
        template = self.get(key)
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            # A malformed template must never break an update handler.
            return template


def _read_messages(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items()}


@cache
def _catalogues(locale: str) -> tuple[dict[str, str], dict[str, str]]:
    settings = get_settings()
    directory = Path(settings.locales_dir)
    fallback = _read_messages(directory / f"{FALLBACK_LOCALE}.json")
    if locale == FALLBACK_LOCALE:
        return fallback, fallback
    return _read_messages(directory / f"{locale}.json"), fallback


def available_locales() -> list[str]:
    """Return the locale codes that ship with the bot."""
    settings = get_settings()
    directory = Path(settings.locales_dir)
    if not directory.is_dir():
        return [FALLBACK_LOCALE]
    return sorted(path.stem for path in directory.glob("*.json"))


def get_localizer(locale: str | None = None) -> Localizer:
    """Build (and cache) a :class:`Localizer` for ``locale``."""
    settings = get_settings()
    default_locale = settings.default_locale or FALLBACK_LOCALE
    code = (locale or default_locale).lower()

    messages, fallback = _catalogues(code)
    if not messages and code != default_locale:
        code = default_locale
        messages, fallback = _catalogues(code)
    if not messages:
        code = FALLBACK_LOCALE
        messages, fallback = _catalogues(code)
    return Localizer(code, messages, fallback)
