from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def create_backup(database_path: Path, backup_dir: Path) -> Path:
    """Copy the database through SQLite's backup API.

    A plain file copy would miss everything still sitting in the write ahead log,
    so the copy is made by SQLite itself, which produces a consistent snapshot.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"bot_{stamp}.sqlite3"

    source = sqlite3.connect(database_path)
    try:
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()

    return target
