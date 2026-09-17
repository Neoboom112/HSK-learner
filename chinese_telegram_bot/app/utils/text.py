from __future__ import annotations

from datetime import datetime, timezone


def progress_bar(value: float, total: float, width: int = 12) -> str:
    if total <= 0:
        return "▱" * width
    filled = max(0, min(width, int(round(width * value / total))))
    return "▰" * filled + "▱" * (width - filled)


def pct(value: float) -> str:
    return f"{value:.1f}%"


def compact_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def format_duration(seconds: int) -> str:
    minutes, sec = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if sec and not parts:
        parts.append(f"{sec}s")
    return " ".join(parts) if parts else "0m"
