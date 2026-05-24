from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

import matplotlib.pyplot as plt


def line_chart(labels: list[str], values: list[float], title: str, ylabel: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        path = Path(tmp.name)
    plt.figure(figsize=(8, 4))
    plt.plot(labels, values, marker="o")
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def heatmap_chart(matrix: list[list[float]], title: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        path = Path(tmp.name)
    plt.figure(figsize=(8, 4))
    plt.imshow(matrix, aspect="auto")
    plt.title(title)
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def progress_bars_chart(labels: list[str], values: list[float], title: str) -> Path:
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        path = Path(tmp.name)
    plt.figure(figsize=(8, 4))
    plt.bar(labels, values)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return path
