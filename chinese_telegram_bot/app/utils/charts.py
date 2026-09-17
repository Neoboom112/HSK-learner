"""Chart helpers. Every function returns the path of a freshly written PNG."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import matplotlib

# The bot has no GUI: render straight to files.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# matplotlib >= 3.6 falls back per glyph, so Latin/Cyrillic come from DejaVu and
# Chinese characters from the first installed CJK font.  Unknown families are
# dropped up front, otherwise matplotlib logs a warning per missing name.
_CANDIDATE_FONTS = (
    "DejaVu Sans",
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
)
_INSTALLED_FONTS = {font.name for font in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = [name for name in _CANDIDATE_FONTS if name in _INSTALLED_FONTS] or ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BAR_COLOR = "#3d8bfd"
EMPTY_COLOR = "#8a8a8a"


def _temp_png() -> Path:
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        return Path(tmp.name)


def reviews_chart(
    daily: list[dict[str, Any]] | None,
    title: str,
    ylabel: str,
    empty_text: str,
    days: int = 14,
) -> Path:
    """Bar chart of reviews per day for the last ``days`` days.

    Missing days are filled with zeroes so the axis stays continuous, and a
    history without reviews draws a placeholder instead of a lone point at zero.
    """
    counts: dict[str, int] = {}
    for row in daily or []:
        key = str(row.get("date") or "")[:10]
        if not key:
            continue
        counts[key] = counts.get(key, 0) + int(row.get("reviews") or 0)

    today = datetime.now(timezone.utc).date()
    window = [today - timedelta(days=offset) for offset in reversed(range(max(1, days)))]
    labels = [day.strftime("%d.%m") for day in window]
    values = [counts.get(day.isoformat(), 0) for day in window]

    path = _temp_png()
    figure, axes = plt.subplots(figsize=(8, 4.2))
    try:
        bars = axes.bar(labels, values, color=BAR_COLOR, width=0.62)
        axes.bar_label(
            bars,
            labels=[str(value) if value else "" for value in values],
            padding=2,
            fontsize=8,
            color="#444444",
        )
        axes.set_title(title, fontsize=12, pad=12)
        axes.set_ylabel(ylabel, fontsize=10)
        axes.grid(axis="y", linestyle="--", alpha=0.35)
        axes.set_axisbelow(True)
        for spine in ("top", "right"):
            axes.spines[spine].set_visible(False)
        axes.tick_params(axis="x", labelrotation=45, labelsize=8)
        axes.tick_params(axis="y", labelsize=8)
        if not any(values):
            axes.set_ylim(0, 1)
            axes.text(
                0.5,
                0.55,
                empty_text,
                transform=axes.transAxes,
                ha="center",
                va="center",
                color=EMPTY_COLOR,
                fontsize=11,
            )
        figure.tight_layout()
        figure.savefig(path, dpi=160)
    finally:
        plt.close(figure)
    return path


def line_chart(labels: list[str], values: list[float], title: str, ylabel: str) -> Path:
    path = _temp_png()
    figure, axes = plt.subplots(figsize=(8, 4.2))
    try:
        axes.plot(labels, values, marker="o", color=BAR_COLOR)
        axes.set_title(title, fontsize=12, pad=12)
        axes.set_ylabel(ylabel, fontsize=10)
        axes.grid(axis="y", linestyle="--", alpha=0.35)
        axes.set_axisbelow(True)
        for spine in ("top", "right"):
            axes.spines[spine].set_visible(False)
        axes.tick_params(axis="x", labelrotation=45, labelsize=8)
        figure.tight_layout()
        figure.savefig(path, dpi=160)
    finally:
        plt.close(figure)
    return path


def heatmap_chart(matrix: list[list[float]], title: str) -> Path:
    path = _temp_png()
    figure, axes = plt.subplots(figsize=(8, 4.2))
    try:
        image = axes.imshow(matrix, aspect="auto")
        axes.set_title(title, fontsize=12, pad=12)
        figure.colorbar(image, ax=axes)
        figure.tight_layout()
        figure.savefig(path, dpi=160)
    finally:
        plt.close(figure)
    return path


def progress_bars_chart(labels: list[str], values: list[float], title: str) -> Path:
    path = _temp_png()
    figure, axes = plt.subplots(figsize=(8, 4.2))
    try:
        axes.bar(labels, values, color=BAR_COLOR)
        axes.set_title(title, fontsize=12, pad=12)
        figure.tight_layout()
        figure.savefig(path, dpi=160)
    finally:
        plt.close(figure)
    return path
