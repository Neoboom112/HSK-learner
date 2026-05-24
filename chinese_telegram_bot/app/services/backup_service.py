from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.utils.backup import create_backup


class BackupService:
    def run_backup(self) -> Path:
        settings = get_settings()
        db_path = settings.db_path
        return create_backup(db_path, Path(settings.backup_dir))
