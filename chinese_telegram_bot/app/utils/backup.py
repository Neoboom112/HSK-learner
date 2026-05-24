from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def create_backup(database_path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"bot_{stamp}.sqlite3"
    shutil.copy2(database_path, target)
    return target
