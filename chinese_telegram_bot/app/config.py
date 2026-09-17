"""Runtime configuration.

Values are read from environment variables, falling back to the ``.env`` file
next to ``main.py``.  Every path is anchored to the project directory so the bot
can be started from anywhere.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Environment backed settings object."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    bot_token: str = ""
    admin_ids: str = ""

    # Localisation
    default_locale: str = "en"
    supported_locales: tuple[str, ...] = ("en", "ru", "zh")

    # Filesystem
    data_dir: Path = BASE_DIR / "data"
    backup_dir: Path = BASE_DIR / "backups"
    locales_dir: Path = BASE_DIR / "locales"

    # Database
    database_url: str = ""
    # Optional explicit database file.  Handy when the project folder sits on a
    # drive that antivirus or a sync client keeps locking.  Empty means
    # ``<DATA_DIR>/bot.db``; relative paths are resolved against the project.
    db_file: str = ""
    sql_echo: bool = False

    # Behaviour
    # Telegram only lets a bot download files up to 20 MB, so that is the cap.
    max_upload_mb: int = 20
    # Automatic "time to review" messages.  Off by default: the user asks for the
    # progress screen themselves.
    review_reminders: bool = False
    daily_review_limit: int = 20
    review_check_seconds: int = 300
    backup_interval_hours: int = 24
    throttle_interval: float = 0.4
    log_level: str = "INFO"

    @property
    def db_path(self) -> Path:
        """Location of the SQLite database file."""
        if self.db_file.strip():
            path = Path(self.db_file.strip())
            return path if path.is_absolute() else BASE_DIR / path
        return self.data_dir / "bot.db"

    @property
    def log_path(self) -> Path:
        """Log file the bot writes next to its data."""
        return BASE_DIR / "logs" / "bot.log"

    @property
    def export_dir(self) -> Path:
        """Directory used by the progress export handlers."""
        return self.data_dir / "exports"

    @property
    def database_dsn(self) -> str:
        """SQLAlchemy async DSN, defaulting to the bundled SQLite database."""
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{self.db_path.as_posix()}"

    @property
    def admin_id_list(self) -> list[int]:
        """Administrator Telegram ids parsed from a comma separated string."""
        result: list[int] = []
        for chunk in self.admin_ids.replace(";", ",").split(","):
            cleaned = chunk.strip()
            if not cleaned:
                continue
            try:
                result.append(int(cleaned))
            except ValueError:
                continue
        return result

    def ensure_directories(self) -> None:
        """Create the working directories the bot writes into."""
        for path in (self.data_dir, self.backup_dir, self.export_dir, Path(self.db_path).parent):
            Path(path).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process wide settings singleton."""
    return Settings()
