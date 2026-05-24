# Chinese Learning Telegram Bot

A local, production-style Telegram bot for learning Chinese with aiogram 3, SQLAlchemy, Alembic, SQLite, APScheduler, and Pydantic.

## Features

- Chinese word learning
- HSK quizzes
- Spaced repetition with SM-2 style scheduling
- Multilingual interface: English, Русский, 中文
- Dictionary upload and management
- CSV / JSON / TXT / APKG import
- APKG export via genanki
- Progress analytics and chart export
- Automatic backups
- Inline keyboards and modern Telegram UX

## Local setup

1. Create and activate a Python 3.12 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set your bot token.
4. Run:

```bash
python main.py
```

## Database

SQLite is used by default. The database file is created at `data/bot.db`.

## Notes

- The bot uses async SQLAlchemy sessions.
- Locale strings live in `locales/en.json`, `locales/ru.json`, and `locales/zh.json`.
- A starter deck is bundled in `data/dictionaries/basic_hsk1.json`.
- Backups are written into `backups/`.

## Alembic

Migrations are included under `migrations/`. Apply them when you prefer migration-based setup instead of `create_all()`.

## Dictionary format

Supported fields:

- hanzi
- pinyin
- translation
- audio
- example_sentence
- hsk_level
- tags
- difficulty
- metadata

The importers accept CSV, JSON, TXT, and APKG.

## Project structure

- `app/handlers`
- `app/services`
- `app/repositories`
- `app/middlewares`
- `app/keyboards`
- `app/utils`
- `app/database`
- `app/models`
- `app/schedulers`
- `locales`
- `data/dictionaries`
- `migrations`

