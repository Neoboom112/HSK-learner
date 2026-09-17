# Chinese Learning Telegram Bot

A Telegram bot for learning Chinese with spaced repetition: HSK decks, your own
dictionaries, flashcards and progress charts.  Built with aiogram 3, SQLAlchemy
(async), Alembic, SQLite, APScheduler and Pydantic.

## Features

- **Spaced repetition** — SM-2 style scheduling, cards come back before you forget them
- **Learning modes** — flashcards, typing, HSK quiz, random and daily review
- **Know / Skip / Don't know** — one tap per card, the translation is revealed with the answer
- **Dictionaries** — the bundled HSK 1 deck, your own decks, and import of
  - Anki packages (`.apkg`): legacy `collection.anki2`, scheduler `collection.anki21` and zstd `collection.anki21b`
  - plain text lists (`颜色 ; yánsè ; цвет`), CSV and JSON
  - deck management: review one deck or all of them, delete a deck with its history
- **Progress** — accuracy, retention, streak, per-day chart of reviews, weak words, export to JSON/CSV/Anki, reset
- **Three languages** — English, Русский, 中文 (interface, charts and the bot profile)
- **No surprises** — the bot never messages you on its own, and errors are reported in your language

## Requirements

- Python 3.12 or newer
- A bot token from [@BotFather](https://t.me/BotFather)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # put your BOT_TOKEN there
python main.py
```

The first start creates `data/bot.db`, switches SQLite to WAL mode and loads the
bundled HSK 1 deck.

## Configuration

Everything is configured through `.env` (all keys are documented in
`.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `BOT_TOKEN` | — | token from @BotFather, required |
| `ADMIN_IDS` | — | comma separated ids allowed to run `/admin` (database backup) |
| `DEFAULT_LOCALE` | `en` | interface language before the user picks one (`en`, `ru`, `zh`) |
| `DATA_DIR` | `data` | dictionaries, database and exports |
| `DB_FILE` | — | optional explicit path of the database file |
| `MAX_UPLOAD_MB` | `20` | upload limit (Telegram caps bot downloads at 20 MB) |
| `REVIEW_REMINDERS` | `false` | let the bot send "time to review" messages |
| `THROTTLE_INTERVAL` | `0.4` | ignore repeated taps faster than this (`0` disables) |
| `LOG_LEVEL` | `INFO` | log level; the same log is written to `logs/bot.log` |

## Commands

`/start`, `/dictionary`, `/progress` and `/help` — the same entries appear in the
Telegram menu.  `/admin` (admins only) makes a database backup.

## Dictionary format

Anki packages are read as they come out of Anki, whichever collection layout they
use.  Text files hold one word per line with the fields separated by `;`, `|` or
a tab:

```
颜色 ; yánsè ; цвет
书包 ; shūbāo ; школьный рюкзак
```

CSV and JSON use the field names `hanzi`, `pinyin`, `translation`, `audio`,
`example_sentence`, `hsk_level`, `tags`, `difficulty` and `metadata`.

## Project layout

```
chinese_telegram_bot/
├── app/
│   ├── handlers/      routers: start, menu, dictionary, learning, progress, admin, errors
│   ├── services/      SRS, learning, dictionaries, import/export, analytics, backup
│   ├── repositories/  one class per table
│   ├── middlewares/   database session, locale, throttling, outbox
│   ├── keyboards/     reply and inline keyboards
│   ├── database/      declarative base, models, async session
│   ├── models/        enums and pydantic schemas
│   └── utils/         Anki reader, charts, text helpers, validators
├── locales/           en.json, ru.json, zh.json
├── migrations/        Alembic revision with the full schema
└── data/              bundled dictionaries and the SQLite database
```

## Database

SQLite in WAL mode.  Tables are created on the first start, and the same schema
is available through Alembic:

```bash
python -m alembic upgrade head
```

Backups are made with SQLite's online backup API, so they stay consistent while
the bot is running.

## License

MIT — see [LICENSE](LICENSE).
