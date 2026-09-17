"""Bot profile: short description, description and the command menu.

Applied on every startup so the texts live in the repository next to the bot
instead of only inside BotFather.
"""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import Settings

logger = logging.getLogger(__name__)

LOCALES = ("en", "ru", "zh")
FALLBACK_LOCALE = "en"

SHORT_DESCRIPTIONS: dict[str, str] = {
    "en": "Chinese learning: HSK flashcards, spaced repetition, your own dictionaries and progress charts.",
    "ru": "Китайский язык: карточки HSK, интервальные повторения, свои словари и графики прогресса.",
    "zh": "学习中文：HSK 闪卡、间隔复习、自定义词典和学习进度图表。",
}

DESCRIPTIONS: dict[str, str] = {
    "en": (
        "Learn Chinese words with spaced repetition.\n\n"
        "• HSK 1 deck is preinstalled, and you can import your own dictionaries "
        "(CSV, JSON, TXT, Anki .apkg)\n"
        "• Modes: flashcards, typing, multiple choice, listening\n"
        "• Reviews are scheduled with SM-2, progress comes with a chart\n"
        "• Export to JSON, CSV or Anki APKG\n\n"
        "Press /start to begin."
    ),
    "ru": (
        "Учим китайские слова с интервальными повторениями.\n\n"
        "• Колода HSK 1 уже внутри, свои словари можно импортировать "
        "(CSV, JSON, TXT, Anki .apkg)\n"
        "• Режимы: карточки, ввод текста, тест, аудирование\n"
        "• Повторения планируются по SM-2, прогресс — с графиком\n"
        "• Экспорт в JSON, CSV и Anki APKG\n\n"
        "Нажмите /start, чтобы начать."
    ),
    "zh": (
        "用间隔复习学习中文词汇。\n\n"
        "• 已内置 HSK 1 词表，也可以导入自己的词典（CSV、JSON、TXT、Anki .apkg）\n"
        "• 模式：闪卡、打字、选择题、听力\n"
        "• 按 SM-2 安排复习，进度带图表\n"
        "• 支持导出 JSON、CSV 和 Anki APKG\n\n"
        "发送 /start 开始使用。"
    ),
}

# command -> localized description
COMMANDS: dict[str, dict[str, str]] = {
    "en": {
        "start": "Main menu",
        "dictionary": "Choose or import a dictionary",
        "progress": "Progress, chart and export",
        "help": "What the bot can do",
    },
    "ru": {
        "start": "Главное меню",
        "dictionary": "Выбрать или импортировать словарь",
        "progress": "Прогресс, график и экспорт",
        "help": "Что умеет бот",
    },
    "zh": {
        "start": "主菜单",
        "dictionary": "选择或导入词典",
        "progress": "进度、图表和导出",
        "help": "机器人功能说明",
    },
}

ADMIN_COMMAND: dict[str, str] = {
    "en": "Admin: database backup",
    "ru": "Админ: бэкап базы",
    "zh": "管理员：数据库备份",
}


def _commands(locale: str, *, admin: bool = False) -> list[BotCommand]:
    catalogue = COMMANDS.get(locale, COMMANDS[FALLBACK_LOCALE])
    result = [BotCommand(command=name, description=text) for name, text in catalogue.items()]
    if admin:
        result.append(
            BotCommand(
                command="admin",
                description=ADMIN_COMMAND.get(locale, ADMIN_COMMAND[FALLBACK_LOCALE]),
            )
        )
    return result


async def apply_bot_profile(bot: Bot, settings: Settings) -> None:
    """Set descriptions and the command menu; failures are logged, not fatal."""
    for locale in LOCALES:
        try:
            await bot.set_my_short_description(
                short_description=SHORT_DESCRIPTIONS[locale],
                language_code=locale,
            )
            await bot.set_my_description(
                description=DESCRIPTIONS[locale],
                language_code=locale,
            )
            await bot.set_my_commands(_commands(locale), language_code=locale)
        except Exception:  # noqa: BLE001 - the bot must start even if this fails
            logger.exception("Could not apply the bot profile for locale %s", locale)

    try:
        await bot.set_my_short_description(short_description=SHORT_DESCRIPTIONS[FALLBACK_LOCALE])
        await bot.set_my_description(description=DESCRIPTIONS[FALLBACK_LOCALE])
        await bot.set_my_commands(_commands(FALLBACK_LOCALE), scope=BotCommandScopeDefault())
    except Exception:  # noqa: BLE001
        logger.exception("Could not apply the default bot profile")

    # Administrators additionally see /admin in their private chat.
    for admin_id in settings.admin_id_list:
        for locale in LOCALES:
            try:
                await bot.set_my_commands(
                    _commands(locale, admin=True),
                    scope=BotCommandScopeChat(chat_id=admin_id),
                    language_code=locale,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Could not apply admin commands for %s", admin_id)
