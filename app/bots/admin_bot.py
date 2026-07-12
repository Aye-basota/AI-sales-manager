import asyncio
import html
import logging
from datetime import datetime, time as dt_time, timezone
from collections.abc import Awaitable, Callable
from typing import Any, List
from uuid import UUID
from zoneinfo import ZoneInfo

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, KeyboardButton, ReplyKeyboardMarkup
from aiogram.types.base import TelegramObject
from sqlalchemy import select, func, delete, or_
from types import SimpleNamespace

from app.config import get_settings
from app.config.telegram import is_configured_bot_token
from app.core.funnel import (
    SALES_STRATEGY_TEMPLATES,
    build_sales_funnel,
    get_first_stage,
    get_max_length_for_stage,
    infer_sales_strategy_from_funnel,
    normalize_sales_strategy,
    sales_strategy_label,
)
from app.core.initial_message_quality import (
    build_initial_message_retry_prompt,
    build_safe_initial_fallback,
    needs_initial_message_retry,
)
from app.core.scheduler import normalize_timezone
from app.db.session import AsyncSessionLocal
from app.llm.engine import LLMEngine
from app.llm.prompts import build_initial_user_prompt, build_system_prompt
from app.models import Script, Campaign, CampaignContact, Conversation, Contact, Message

logger = logging.getLogger(__name__)

settings = get_settings()
_bot: Bot | None = None
_polling_active = False
_command_registration_task: asyncio.Task | None = None
dp = Dispatcher(storage=MemoryStorage())
router = Router()

MENU_SCRIPTS = "🧭 Бизнесы"
MENU_NEW_SCRIPT = "➕ Новый бизнес"
MENU_CAMPAIGNS = "🚀 Запуски"
MENU_START_CAMPAIGN = "▶️ Черновики"
MENU_UPLOAD = "👥 Контакты и запуск"
MENU_DISCOVER = "🔎 Поиск лидов"
MENU_HOT_LEADS = "🔥 Горячие лиды"
MENU_HELP = "❓ Помощь"
MENU_CONVERSATIONS = "💬 Диалоги"
MENU_ANALYTICS = "📊 Аналитика"
MENU_SCRIPTS_EN = "🧭 Businesses"
MENU_NEW_SCRIPT_EN = "➕ New business"
MENU_CAMPAIGNS_EN = "🚀 Launches"
MENU_START_CAMPAIGN_EN = "▶️ Drafts"
MENU_UPLOAD_EN = "👥 Contacts & launch"
MENU_DISCOVER_EN = "🔎 Lead sources"
MENU_HOT_LEADS_EN = "🔥 Hot leads"
MENU_HELP_EN = "❓ Help"
MENU_CONVERSATIONS_EN = "💬 Conversations"
MENU_ANALYTICS_EN = "📊 Analytics"

LANG_RU = "ru"
LANG_EN = "en"
_admin_language_by_user: dict[int, str] = {}

UNKNOWN_ADMIN_REPLY = (
    "Не понял команду.\n\n"
    "Откройте меню ниже или напишите /help.\n\n"
    "Обычный путь: опишите бизнес, загрузите контакты, проверьте первое "
    "сообщение и запустите рассылку."
)
UNKNOWN_ADMIN_REPLY_EN = (
    "I did not understand that command.\n\n"
    "Use the menu below or send /help.\n\n"
    "Simple flow: describe the business, upload contacts, review the first message, "
    "and launch outreach."
)
ACTIVE_WIZARD_REPLY = (
    "Сейчас открыт мастер настройки.\n\n"
    "Ответьте на последний вопрос, нажмите кнопку в сообщении выше, напишите "
    "назад, чтобы вернуться на шаг назад, или /cancel для выхода."
)
ACTIVE_WIZARD_REPLY_EN = (
    "A setup wizard is open.\n\n"
    "Answer the last question, press a button in the message above, type back to return "
    "one step, or use /cancel to exit."
)
ADMIN_ERROR_REPLY = (
    "Что-то пошло не так, но бот не упал молча.\n\n"
    "Попробуйте открыть /start или /help. Ошибка записана в логи, чтобы ее можно "
    "было быстро разобрать."
)
ADMIN_ERROR_REPLY_EN = (
    "Something went wrong, but the bot did not fail silently.\n\n"
    "Try /start or /help. The error was written to logs so it can be investigated."
)

TONE_OPTIONS = ["Деловой", "Дружелюбный", "Агрессивный"]
TONE_OPTIONS_EN = ["Professional", "Friendly", "Direct"]
TONE_MAP = {
    "Деловой": "professional",
    "Дружелюбный": "friendly",
    "Агрессивный": "aggressive",
    "Professional": "professional",
    "Friendly": "friendly",
    "Direct": "aggressive",
}

MENU_LABELS = {
    LANG_RU: {
        "scripts": MENU_SCRIPTS,
        "new_script": MENU_NEW_SCRIPT,
        "campaigns": MENU_CAMPAIGNS,
        "start_campaign": MENU_START_CAMPAIGN,
        "upload": MENU_UPLOAD,
        "discover": MENU_DISCOVER,
        "hot_leads": MENU_HOT_LEADS,
        "help": MENU_HELP,
        "conversations": MENU_CONVERSATIONS,
        "analytics": MENU_ANALYTICS,
        "placeholder": "Выберите действие",
    },
    LANG_EN: {
        "scripts": MENU_SCRIPTS_EN,
        "new_script": MENU_NEW_SCRIPT_EN,
        "campaigns": MENU_CAMPAIGNS_EN,
        "start_campaign": MENU_START_CAMPAIGN_EN,
        "upload": MENU_UPLOAD_EN,
        "discover": MENU_DISCOVER_EN,
        "hot_leads": MENU_HOT_LEADS_EN,
        "help": MENU_HELP_EN,
        "conversations": MENU_CONVERSATIONS_EN,
        "analytics": MENU_ANALYTICS_EN,
        "placeholder": "Choose an action",
    },
}

STATE_LABELS = {
    LANG_RU: {
        "cold": "первый контакт",
        "warm": "есть интерес",
        "hot": "готов к передаче",
        "meeting_booked": "созвон согласован",
        "objection_handler": "есть возражение",
        "closed": "закрыт",
    },
    LANG_EN: {
        "cold": "first touch",
        "warm": "interested",
        "hot": "ready for handoff",
        "meeting_booked": "meeting agreed",
        "objection_handler": "has an objection",
        "closed": "closed",
    },
}
SENTIMENT_LABELS = {
    LANG_RU: {
        "positive": "позитивное",
        "neutral": "нейтральное",
        "negative": "негативное",
        None: "не определено",
        "": "не определено",
    },
    LANG_EN: {
        "positive": "positive",
        "neutral": "neutral",
        "negative": "negative",
        None: "not detected",
        "": "not detected",
    },
}


def _user_id_from_event(event: Any) -> int | None:
    user = getattr(event, "from_user", None)
    if user and getattr(user, "id", None) is not None:
        if getattr(user, "is_bot", False):
            chat = getattr(event, "chat", None)
            if chat and getattr(chat, "id", None) is not None:
                return int(chat.id)
        return int(user.id)
    chat = getattr(event, "chat", None)
    if chat and getattr(chat, "id", None) is not None:
        return int(chat.id)
    message = getattr(event, "message", None)
    user = getattr(message, "from_user", None)
    if user and getattr(user, "id", None) is not None:
        if getattr(user, "is_bot", False):
            chat = getattr(message, "chat", None)
            if chat and getattr(chat, "id", None) is not None:
                return int(chat.id)
        return int(user.id)
    chat = getattr(message, "chat", None)
    if chat and getattr(chat, "id", None) is not None:
        return int(chat.id)
    return None


def _admin_lang(event: Any | None = None) -> str:
    user_id = _user_id_from_event(event) if event is not None else None
    if user_id is None:
        return LANG_RU
    return _admin_language_by_user.get(user_id, LANG_RU)


def _set_admin_lang(event: Any, lang: str) -> str:
    lang = LANG_EN if lang == LANG_EN else LANG_RU
    user_id = _user_id_from_event(event)
    if user_id is not None:
        _admin_language_by_user[user_id] = lang
    return lang


def _menu_label(key: str, lang: str = LANG_RU) -> str:
    labels = MENU_LABELS.get(lang, MENU_LABELS[LANG_RU])
    return labels[key]


COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="help", description="Помощь и схема"),
    BotCommand(command="cancel", description="Отменить текущий мастер"),
    BotCommand(command="back", description="Вернуться на шаг назад"),
    BotCommand(command="scripts", description="Бизнесы и настройки"),
    BotCommand(command="campaigns", description="Запуски и статусы"),
    BotCommand(command="upload", description="Загрузить контакты и запустить"),
    BotCommand(command="analytics", description="Аналитика"),
    BotCommand(command="hotleads", description="Горячие лиды"),
    BotCommand(command="newscript", description="Описать новый бизнес"),
    BotCommand(command="startcampaign", description="Запустить черновик"),
    BotCommand(command="discover", description="Поиск лидов"),
    BotCommand(command="conversations", description="История по contact_id"),
]

COMMAND_REGISTRATION_ATTEMPTS = 3
COMMAND_REGISTRATION_TIMEOUT_S = 10
COMMAND_REGISTRATION_RETRY_DELAY_S = 3


def _main_menu_keyboard(lang: str = LANG_RU) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_menu_label("scripts", lang)),
                KeyboardButton(text=_menu_label("new_script", lang)),
            ],
            [
                KeyboardButton(text=_menu_label("campaigns", lang)),
                KeyboardButton(text=_menu_label("start_campaign", lang)),
            ],
            [
                KeyboardButton(text=_menu_label("upload", lang)),
                KeyboardButton(text=_menu_label("discover", lang)),
            ],
            [
                KeyboardButton(text=_menu_label("hot_leads", lang)),
                KeyboardButton(text=_menu_label("conversations", lang)),
            ],
            [
                KeyboardButton(text=_menu_label("analytics", lang)),
                KeyboardButton(text=_menu_label("help", lang)),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=_menu_label("placeholder", lang),
    )


def _language_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
                types.InlineKeyboardButton(text="English", callback_data="lang:en"),
            ]
        ]
    )


def _welcome_text(lang: str) -> str:
    if lang == LANG_EN:
        return (
            "Ready.\n\n"
            "Simple flow:\n"
            "1. Describe the business: what you sell, who you sell to, and how the manager should talk.\n"
            "2. Upload contacts.\n"
            "3. Review the first message and launch.\n"
            "4. Track replies in Hot leads and Conversations.\n\n"
            "A good place to start is New business or Contacts & launch."
        )
    return (
        "Готов к работе.\n\n"
        "Самый простой путь:\n"
        "1. Опишите бизнес: что продаете, кому и как менеджер должен общаться.\n"
        "2. Загрузите контакты.\n"
        "3. Проверьте первое сообщение и запустите.\n"
        "4. Ответы смотрите в горячих лидах и диалогах.\n\n"
        "Начать лучше с «Новый бизнес» или «Контакты и запуск»."
    )


@dp.startup()
async def on_startup(bot: Bot):
    global _command_registration_task, _polling_active
    _command_registration_task = asyncio.create_task(_set_admin_bot_commands(bot))
    _polling_active = True
    logger.info("Admin bot polling startup completed")


@dp.shutdown()
async def on_shutdown(bot: Bot):
    global _command_registration_task, _polling_active
    _polling_active = False
    if _command_registration_task and not _command_registration_task.done():
        _command_registration_task.cancel()
        try:
            await _command_registration_task
        except asyncio.CancelledError:
            pass
    _command_registration_task = None
    logger.info("Admin bot polling shutdown completed")


async def _set_admin_bot_commands(bot: Bot) -> bool:
    for attempt in range(1, COMMAND_REGISTRATION_ATTEMPTS + 1):
        try:
            await asyncio.wait_for(
                bot.set_my_commands(COMMANDS),
                timeout=COMMAND_REGISTRATION_TIMEOUT_S,
            )
            logger.info("Admin bot commands registered")
            return True
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "Admin bot commands registration attempt %s/%s failed: %s",
                attempt,
                COMMAND_REGISTRATION_ATTEMPTS,
                exc.__class__.__name__,
            )
            if attempt < COMMAND_REGISTRATION_ATTEMPTS:
                await asyncio.sleep(COMMAND_REGISTRATION_RETRY_DELAY_S)
    logger.warning(
        "Admin bot commands were not registered after %s attempts; polling continues",
        COMMAND_REGISTRATION_ATTEMPTS,
    )
    return False


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.admin_bot_token)
    return _bot


def is_admin_bot_configured() -> bool:
    return is_configured_bot_token(settings.admin_bot_token)


def is_admin_bot_running() -> bool:
    return _polling_active


# ---------------------------------------------------------------------------
# FSM States
# ---------------------------------------------------------------------------


class ScriptCreateFSM(StatesGroup):
    name = State()
    role_prompt = State()
    target_audience = State()
    goal = State()
    success_criteria = State()
    tone = State()
    sales_strategy = State()
    first_message_goal = State()
    call_to_action = State()
    language = State()
    emoji_policy = State()
    max_first_message_length = State()
    max_messages = State()
    follow_up_delay_hours = State()
    working_hours = State()
    working_hours_end = State()
    timezone = State()
    confirm = State()


class ScriptEditFSM(StatesGroup):
    value = State()


class CSVImportFSM(StatesGroup):
    waiting_file = State()
    preview = State()


class CampaignCreateFSM(StatesGroup):
    select_script = State()
    preview = State()
    name = State()
    confirm = State()


class CampaignStartFSM(StatesGroup):
    selecting = State()


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


SCRIPT_FIELD_KEYS = {
    "name": "name",
    "role": "role_prompt",
    "aud": "target_audience",
    "goal": "goal",
    "crit": "success_criteria",
    "tone": "tone",
    "strategy": "sales_strategy",
    "cta": "call_to_action",
    "msg": "max_messages",
    "follow": "follow_up_delay_hours",
    "hours": "working_hours",
    "tz": "timezone",
}
SCRIPT_FIELD_LABELS = {
    "name": "Название",
    "role_prompt": "Описание бизнеса",
    "target_audience": "Целевая аудитория",
    "goal": "Цель AI-менеджера",
    "success_criteria": "Когда считать успехом",
    "tone": "Стиль общения",
    "sales_strategy": "Воронка продаж",
    "call_to_action": "Предложение следующего шага",
    "max_messages": "Лимит сообщений на контакт",
    "follow_up_delay_hours": "Напоминание, если лид молчит",
    "working_hours": "Рабочие часы",
    "timezone": "Часовой пояс",
}
SCRIPT_FIELD_LABELS_EN = {
    "name": "Name",
    "role_prompt": "Business description",
    "target_audience": "Target audience",
    "goal": "Manager goal",
    "success_criteria": "Success criteria",
    "tone": "Communication style",
    "sales_strategy": "Sales funnel",
    "call_to_action": "Next-step offer",
    "max_messages": "Message limit per contact",
    "follow_up_delay_hours": "Follow-up delay",
    "working_hours": "Working hours",
    "timezone": "Timezone",
}
SCRIPT_STRATEGY_CALLBACK_CODES = {
    "n": "nurture",
    "q": "quick_call",
    "c": "consultative",
    "l": "qualification",
}
SCRIPT_STRATEGY_CALLBACK_KEYS = {
    value: key for key, value in SCRIPT_STRATEGY_CALLBACK_CODES.items()
}
HISTORY_ORIGIN_CALLBACK_CODES = {
    "m": "message",
    "h": "hotleads",
    "c": "conversations",
}
HISTORY_ORIGIN_CALLBACK_KEYS = {
    value: key for key, value in HISTORY_ORIGIN_CALLBACK_CODES.items()
}

CAMPAIGN_STATUS_LABELS = {
    LANG_RU: {
        "draft": "черновик",
        "running": "идет отправка",
        "paused": "на паузе",
        "completed": "завершен",
        "closed": "закрыт",
    },
    LANG_EN: {
        "draft": "draft",
        "running": "running",
        "paused": "paused",
        "completed": "completed",
        "closed": "closed",
    },
}


def _html(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _compact(value: Any, limit: int = 170) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return "—"
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _format_time(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    text = str(value or "")
    return text[:5] if text else "—"


def _campaign_status_label(status: str | None, lang: str = LANG_RU) -> str:
    labels = CAMPAIGN_STATUS_LABELS.get(lang, CAMPAIGN_STATUS_LABELS[LANG_RU])
    return labels.get(status or "", (status or "—").replace("_", " "))


def _strategy_from_script(script: Script) -> str:
    return infer_sales_strategy_from_funnel(getattr(script, "sales_funnel", None))


def _script_strategy_callback_data(strategy_key: str, script_id: UUID) -> str:
    code = SCRIPT_STRATEGY_CALLBACK_KEYS.get(strategy_key, strategy_key)
    return f"ss:{code}:{script_id}"


def _parse_script_strategy_callback(data: str) -> tuple[str, UUID]:
    if data.startswith("ss:"):
        _, strategy_code, script_id_raw = data.split(":", 2)
        strategy_key = SCRIPT_STRATEGY_CALLBACK_CODES[strategy_code]
        return strategy_key, UUID(script_id_raw)

    _, strategy_raw, script_id_raw = data.split(":", 2)
    strategy_key = normalize_sales_strategy(strategy_raw)
    return strategy_key, UUID(script_id_raw)


def _format_script_summary(
    script: Script,
    campaign_count: int = 0,
    lang: str = LANG_RU,
) -> str:
    status = (
        ("✅ active" if script.is_active else "⏸ off")
        if lang == LANG_EN
        else ("✅ активен" if script.is_active else "⏸ выключен")
    )
    strategy = sales_strategy_label(_strategy_from_script(script), lang)
    if lang == LANG_EN:
        launches = "launch" if campaign_count == 1 else "launches"
        return (
            f"<b>{_html(script.name)}</b> · {status}\n"
            f"Goal: {_html(_compact(script.goal, 120))}\n"
            f"Audience: {_html(_compact(script.target_audience, 110))}\n"
            f"Funnel: {_html(strategy)}\n"
            f"Used in {campaign_count} {launches}"
        )
    return (
        f"<b>{_html(script.name)}</b> · {status}\n"
        f"Цель: {_html(_compact(script.goal, 120))}\n"
        f"Аудитория: {_html(_compact(script.target_audience, 110))}\n"
        f"Воронка: {_html(strategy)}\n"
        f"Запусков с этим бизнесом: {campaign_count}"
    )


def _format_script_details(
    script: Script,
    campaign_count: int = 0,
    lang: str = LANG_RU,
) -> str:
    status = (
        ("active" if script.is_active else "off")
        if lang == LANG_EN
        else ("активен" if script.is_active else "выключен")
    )
    working_hours = (
        f"{_format_time(script.working_hours_start)}-{_format_time(script.working_hours_end)}"
    )
    strategy = sales_strategy_label(_strategy_from_script(script), lang)
    if lang == LANG_EN:
        return (
            f"<b>{_html(script.name)}</b>\n\n"
            f"Status: {status}\n"
            f"Launches using this business: {campaign_count}\n\n"
            f"<b>What we sell / who we are</b>\n{_html(_compact(script.role_prompt, 900))}\n\n"
            f"<b>Who we write to</b>\n{_html(_compact(script.target_audience, 600))}\n\n"
            f"<b>Manager goal</b>\n{_html(_compact(script.goal, 600))}\n\n"
            f"<b>Success</b>\n{_html(_compact(script.success_criteria, 600))}\n\n"
            f"<b>Style and behavior</b>\n"
            f"Tone: {_html(script.tone or 'professional')}\n"
            f"Sales funnel: {_html(strategy)}\n"
            f"Next step: {_html(getattr(script, 'call_to_action', None) or 'short 10-minute call')}\n"
            f"Messages per contact: {script.max_messages or 2}\n"
            f"Follow-up: after {script.follow_up_delay_hours or 24} h if no answer\n"
            f"Working hours: {working_hours}, {_html(script.timezone or 'Europe/Moscow')}"
        )
    return (
        f"<b>{_html(script.name)}</b>\n\n"
        f"Статус: {status}\n"
        f"Запусков с этим бизнесом: {campaign_count}\n\n"
        f"<b>Что продаем / кто мы</b>\n{_html(_compact(script.role_prompt, 900))}\n\n"
        f"<b>Кому пишем</b>\n{_html(_compact(script.target_audience, 600))}\n\n"
        f"<b>Цель менеджера</b>\n{_html(_compact(script.goal, 600))}\n\n"
        f"<b>Успех</b>\n{_html(_compact(script.success_criteria, 600))}\n\n"
        f"<b>Стиль и поведение</b>\n"
        f"Тон: {_html(script.tone or 'professional')}\n"
        f"Воронка продаж: {_html(strategy)}\n"
        f"Следующий шаг: {_html(getattr(script, 'call_to_action', None) or '15-минутный созвон')}\n"
        f"Сообщений на контакт: {script.max_messages or 2}\n"
        f"Напоминание: через {script.follow_up_delay_hours or 24} ч, если нет ответа\n"
        f"Рабочее время: {working_hours}, {_html(script.timezone or 'Europe/Moscow')}"
    )


def _resolve_timezone_input(value: str | None) -> str | None:
    timezone_name = normalize_timezone(value or "Europe/Moscow")
    try:
        ZoneInfo(timezone_name)
    except Exception:
        return None
    return timezone_name


def _parse_working_hours(text: str) -> tuple[dt_time, dt_time] | None:
    try:
        parts = text.split("-")
        if len(parts) != 2:
            return None
        start_str, end_str = parts[0].strip(), parts[1].strip()
        h1, m1 = map(int, start_str.split(":"))
        h2, m2 = map(int, end_str.split(":"))
        return dt_time(h1, m1), dt_time(h2, m2)
    except (TypeError, ValueError):
        return None


def _time_in_working_window(current: dt_time, start: dt_time, end: dt_time) -> bool:
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def _launch_timing_notice(script: Script | None, lang: str = LANG_RU) -> str:
    if not script:
        return ""
    timezone_name = getattr(script, "timezone", None) or "Europe/Moscow"
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo("Europe/Moscow")
        timezone_name = "Europe/Moscow"
    start = script.working_hours_start or dt_time(9, 0)
    end = script.working_hours_end or dt_time(18, 0)
    now_local = datetime.now(tz).time()
    if _time_in_working_window(now_local, start, end):
        return ""
    window = f"{_format_time(start)}-{_format_time(end)} {timezone_name}"
    if lang == LANG_EN:
        return (
            "\n\nNote: it is outside this business's working hours now. "
            f"Messages will be sent during {window}."
        )
    return (
        "\n\nВажно: сейчас вне рабочих часов этого бизнеса. "
        f"Сообщения уйдут в окно {window}."
    )


def _launch_queue_notice(total_contacts: int, lang: str = LANG_RU) -> str:
    if lang == LANG_EN:
        return (
            "\n\nSending order:\n"
            "1. Contacts are processed in upload order.\n"
            "2. The first pass starts right away, then the scheduler checks the queue every 5 minutes.\n"
            "3. One seller account sends no more than 1 message per 30 seconds."
        )
    last_two = total_contacts % 100
    last_one = total_contacts % 10
    if last_one == 1 and last_two != 11:
        contact_word = "контакт"
    elif 2 <= last_one <= 4 and not 12 <= last_two <= 14:
        contact_word = "контакта"
    else:
        contact_word = "контактов"
    return (
        "\n\nКак пойдет отправка:\n"
        f"1. В очереди {total_contacts} {contact_word}; порядок такой же, как в файле.\n"
        "2. Первый проход запускается сразу, дальше очередь проверяется каждые 5 минут.\n"
        "3. Один Telegram-аккаунт отправляет не чаще 1 сообщения в 30 секунд."
    )


def _script_field_prompt(field: str, lang: str = LANG_RU) -> str:
    if lang == LANG_EN:
        prompts = {
            "name": "Enter a short business or offer name:",
            "role_prompt": (
                "Describe the business in plain language: what you sell, who you help, "
                "and what makes it valuable. The more concrete this is, the less the model will guess."
            ),
            "target_audience": "Who are we writing to? Roles, industries, company size. Send '-' to leave empty.",
            "goal": "What should the manager achieve? Example: spark interest and offer a short call.",
            "success_criteria": "When should the conversation count as successful? Send '-' to leave empty.",
            "tone": "Enter style: professional, friendly, or aggressive. Usually friendly is best.",
            "sales_strategy": "Choose the sales funnel:",
            "call_to_action": "What next step should be offered? Example: a short 10-minute call.",
            "max_messages": "Maximum messages per contact? Usually 2 or 3.",
            "follow_up_delay_hours": "After how many hours should we follow up if the lead is silent? Example: 24.",
            "working_hours": "Enter working hours as HH:MM-HH:MM, for example 09:00-18:00.",
            "timezone": "Enter timezone, for example Europe/Moscow, UTC, or msk.",
        }
        return prompts.get(field, "Enter the new value:")
    prompts = {
        "name": "Введите короткое название бизнеса или оффера:",
        "role_prompt": (
            "Опишите бизнес простыми словами: что продаете, кому помогаете, "
            "в чем ценность. Чем конкретнее описание, тем меньше модель будет додумывать."
        ),
        "target_audience": "Кому пишем? Можно указать должности, отрасли, размер компаний. '-' чтобы оставить пустым.",
        "goal": "Что должен сделать AI-менеджер? Например: заинтересовать и предложить короткий созвон.",
        "success_criteria": "Когда считать диалог успешным? '-' чтобы оставить пустым.",
        "tone": "Введите стиль: professional, friendly или aggressive. Обычно лучше friendly.",
        "sales_strategy": "Выберите воронку продаж:",
        "call_to_action": "Какой следующий шаг предлагать лиду? Например: короткий 10-минутный созвон.",
        "max_messages": "Сколько сообщений максимум отправлять одному контакту? Обычно 2 или 3.",
        "follow_up_delay_hours": "Через сколько часов мягко напомнить, если лид молчит? Например: 24.",
        "working_hours": "Введите рабочие часы в формате HH:MM-HH:MM, например 09:00-18:00.",
        "timezone": "Введите часовой пояс, например Europe/Moscow, UTC или msk.",
    }
    return prompts.get(field, "Введите новое значение:")


def _format_scripts(scripts: List, lang: str = LANG_RU) -> str:
    lines = []
    for item in scripts:
        try:
            s, campaign_count = item[0], item[1]
        except Exception:
            s, campaign_count = item, 0
        lines.append(_format_script_summary(s, campaign_count, lang))
    if not lines:
        return ""
    header = (
        "Businesses. Open a card to view or edit the full setup."
        if lang == LANG_EN
        else "Бизнесы. Откройте карточку, чтобы посмотреть или изменить полную настройку."
    )
    return header + "\n\n" + "\n\n".join(lines)


def _format_campaigns(campaigns: List, lang: str = LANG_RU) -> str:
    lines = []
    for item in campaigns:
        try:
            c, script = item[0], item[1]
        except Exception:
            c, script = item, None
        script_name = script.name if script else "—"
        if lang == LANG_EN:
            lines.append(
                f"📢 <b>{_html(c.name)}</b>\n"
                f"Business: {_html(script_name)}\n"
                f"Status: {_campaign_status_label(c.status, lang)}\n"
                f"Contacts: {c.processed_contacts}/{c.total_contacts}\n"
                f"Replies: {c.replied_count} | Qualified: {c.qualified_count} | Meetings: {c.meeting_booked_count}"
            )
        else:
            lines.append(
                f"📢 <b>{_html(c.name)}</b>\n"
                f"Бизнес: {_html(script_name)}\n"
                f"Статус: {_campaign_status_label(c.status, lang)}\n"
                f"Контакты: {c.processed_contacts}/{c.total_contacts}\n"
                f"Ответили: {c.replied_count} | Квалифицированы: "
                f"{c.qualified_count} | Встречи: {c.meeting_booked_count}"
            )
    return "\n\n".join(lines)


def _state_label(state: str | None, lang: str = LANG_RU) -> str:
    labels = STATE_LABELS.get(lang, STATE_LABELS[LANG_RU])
    if not state:
        return labels.get("cold", "первый контакт")
    return labels.get(state, state.replace("_", " "))


def _sentiment_label(sentiment: str | None, lang: str = LANG_RU) -> str:
    labels = SENTIMENT_LABELS.get(lang, SENTIMENT_LABELS[LANG_RU])
    return labels.get(sentiment, sentiment or labels.get(None, "—"))


def _contact_display_name(contact: Contact) -> str:
    if contact.telegram_username:
        return contact.telegram_username
    full_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    if full_name and contact.phone:
        return f"{full_name} · {contact.phone}"
    return full_name or contact.phone or contact.company_name or str(contact.id)[:8]


def _conversation_id_from_row(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    candidate = getattr(value, "id", None)
    return candidate if isinstance(candidate, UUID) else None


def _build_campaign_buttons(campaign, lang: str = LANG_RU) -> list:
    """Return action buttons appropriate for the campaign status."""
    status = campaign.status
    name = campaign.name[:18]
    delete_text = "Delete" if lang == LANG_EN else "Удалить"
    pause_text = "Pause" if lang == LANG_EN else "Пауза"
    resume_text = "Resume" if lang == LANG_EN else "Запустить"
    start_text = "Start" if lang == LANG_EN else "Запустить"

    if status == "draft":
        return [
            types.InlineKeyboardButton(
                text=f"▶️ {start_text}: {name}", callback_data=f"camp_start:{campaign.id}"
            ),
            types.InlineKeyboardButton(
                text=f"🗑 {delete_text}: {name}", callback_data=f"camp_delete:{campaign.id}"
            ),
        ]
    elif status == "running":
        return [
            types.InlineKeyboardButton(
                text=f"⏸ {pause_text}: {name}", callback_data=f"camp_pause:{campaign.id}"
            ),
            types.InlineKeyboardButton(
                text=f"🗑 {delete_text}: {name}", callback_data=f"camp_delete:{campaign.id}"
            ),
        ]
    elif status == "paused":
        return [
            types.InlineKeyboardButton(
                text=f"▶️ {resume_text}: {name}", callback_data=f"camp_resume:{campaign.id}"
            ),
            types.InlineKeyboardButton(
                text=f"🗑 {delete_text}: {name}", callback_data=f"camp_delete:{campaign.id}"
            ),
        ]
    else:
        return [
            types.InlineKeyboardButton(
                text=f"🗑 {delete_text}: {name}", callback_data=f"camp_delete:{campaign.id}"
            )
        ]


def _build_script_buttons(scripts: List, lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    rows = [
        [
            types.InlineKeyboardButton(
                text="➕ New business" if lang == LANG_EN else "➕ Описать бизнес",
                callback_data="script_new",
            )
        ]
    ]
    for item in scripts:
        try:
            script, campaign_count = item[0], item[1]
        except Exception:
            script, campaign_count = item, 0

        name = _compact(script.name or "Бизнес", 18)
        if lang == LANG_EN:
            view_text = "Open"
            edit_text = "Edit"
            toggle_text = "⏸ Turn off" if script.is_active else "▶️ Turn on"
            delete_text = "Delete"
        else:
            view_text = "Открыть"
            edit_text = "Изменить"
            toggle_text = "⏸ Выключить" if script.is_active else "▶️ Включить"
            delete_text = "Удалить"
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"👁 {view_text}: {name}", callback_data=f"scriptv:{script.id}"
                ),
                types.InlineKeyboardButton(
                    text=f"✏️ {edit_text}: {name}", callback_data=f"scripte:{script.id}"
                ),
            ]
        )
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{toggle_text} {name}",
                    callback_data=f"script_toggle:{script.id}",
                )
            ]
        )
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"🗑 {delete_text}: {name}",
                    callback_data=f"script_delete:{script.id}:{campaign_count}",
                )
            ]
        )

    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _format_hotleads(rows: List, lang: str = LANG_RU) -> str:
    lines = []
    for idx, (conv, contact) in enumerate(rows, 1):
        name = _contact_display_name(contact)
        state_emoji = "🔥" if conv.current_state == "hot" else "📅"
        status_label = _state_label(conv.current_state, lang)
        sentiment_label = _sentiment_label(conv.sentiment, lang)
        operator_status = getattr(conv, "operator_status", None)
        operator_line = ""
        if operator_status:
            if lang == LANG_EN:
                operator_line = f"\nOperator note: {operator_status.replace('_', ' ')}"
            else:
                operator_line = f"\nРучная отметка: {operator_status.replace('_', ' ')}"
        lines.append(
            f"{idx}. {state_emoji} <b>{name}</b>\n"
            f"{'Status' if lang == LANG_EN else 'Статус'}: {status_label}\n"
            f"{'Tone' if lang == LANG_EN else 'Настроение'}: {sentiment_label}"
            f"{operator_line}"
        )
    return "\n\n".join(lines)


def _format_hotlead_detail(conv: Conversation, contact: Contact, lang: str = LANG_RU) -> str:
    name = _contact_display_name(contact)
    status = _state_label(conv.current_state, lang)
    sentiment = _sentiment_label(conv.sentiment, lang)
    operator_status = (getattr(conv, "operator_status", None) or "—").replace("_", " ")
    if lang == LANG_EN:
        return (
            f"<b>{_html(name)}</b>\n\n"
            f"Status: {status}\n"
            f"Tone: {sentiment}\n"
            f"Operator note: {operator_status}\n"
            f"Contact ID: <code>{contact.id}</code>\n\n"
            "Use Qualified when the lead is worth handing to a human manager. "
            "Use Not a fit when the lead should be excluded from follow-up."
        )
    return (
        f"<b>{_html(name)}</b>\n\n"
        f"Статус: {status}\n"
        f"Настроение: {sentiment}\n"
        f"Ручная отметка: {operator_status}\n"
        f"contact_id: <code>{contact.id}</code>\n\n"
        "«Готов к работе» значит: лида можно передавать человеку. "
        "«Не целевой» значит: не брать в дальнейший follow-up."
    )


def _hotlead_overview_keyboard(rows: List, lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    button_prefix = "Open" if lang == LANG_EN else "Открыть"
    refresh_text = "🔄 Refresh" if lang == LANG_EN else "🔄 Обновить"
    kb_rows = []
    for idx, (conv, contact) in enumerate(rows, 1):
        name = _compact(_contact_display_name(contact), 22)
        status = _state_label(conv.current_state, lang)
        kb_rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{idx}. {button_prefix}: {name} · {status}",
                    callback_data=f"lead:{conv.id}",
                )
            ]
        )
    kb_rows.append([types.InlineKeyboardButton(text=refresh_text, callback_data="refresh_hotleads")])
    return types.InlineKeyboardMarkup(inline_keyboard=kb_rows)


def _hotlead_detail_keyboard(conv_id: UUID, lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    if lang == LANG_EN:
        rows = [
            [types.InlineKeyboardButton(text="📜 Open conversation", callback_data=f"history:{conv_id}:hotleads")],
            [
                types.InlineKeyboardButton(text="✅ Mark qualified", callback_data=f"qualify:{conv_id}"),
                types.InlineKeyboardButton(text="🚫 Not a fit", callback_data=f"reject:{conv_id}"),
            ],
            [types.InlineKeyboardButton(text="← Back to hot leads", callback_data="hotleads:list")],
        ]
    else:
        rows = [
            [types.InlineKeyboardButton(text="📜 Открыть диалог", callback_data=f"history:{conv_id}:hotleads")],
            [
                types.InlineKeyboardButton(text="✅ Готов к работе", callback_data=f"qualify:{conv_id}"),
                types.InlineKeyboardButton(text="🚫 Не целевой", callback_data=f"reject:{conv_id}"),
            ],
            [types.InlineKeyboardButton(text="← К горячим лидам", callback_data="hotleads:list")],
        ]
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _format_analytics(
    total_contacts: int,
    sent: int,
    replied: int,
    hot: int,
    meetings: int,
    rejected: int = 0,
    avg_length: float = 0.0,
    lang: str = LANG_RU,
) -> str:
    reply_rate = (replied / sent * 100) if sent else 0
    if lang == LANG_EN:
        return (
            "📊 Summary\n\n"
            f"Total contacts: {total_contacts}\n"
            f"Sent: {sent}\n"
            f"Replied: {replied} ({reply_rate:.1f}%)\n"
            f"Hot leads: {hot}\n"
            f"Meetings: {meetings}\n"
            f"Guardrail fallbacks: {rejected}\n"
            f"Average message length: {avg_length:.0f} chars"
        )
    return (
        "📊 Сводка\n\n"
        f"Всего контактов: {total_contacts}\n"
        f"Отправлено: {sent}\n"
        f"Ответили: {replied} ({reply_rate:.1f}%)\n"
        f"Горячие лиды: {hot}\n"
        f"Встречи: {meetings}\n"
        f"Guardrails отказов: {rejected}\n"
        f"Средняя длина сообщения: {avg_length:.0f} симв."
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Выберите язык интерфейса.\nChoose interface language.",
        reply_markup=_language_keyboard(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def handle_language_choice(callback: types.CallbackQuery):
    lang = _set_admin_lang(callback, callback.data.split(":", 1)[1])
    text = _welcome_text(lang)
    saved_text = "Language: English" if lang == LANG_EN else "Язык: русский"
    if callback.message:
        try:
            await callback.message.edit_text(saved_text)
        except TelegramBadRequest as exc:
            if not _is_message_not_modified(exc):
                await callback.message.answer(saved_text)
        await callback.message.answer(text, reply_markup=_main_menu_keyboard(lang))
    await callback.answer("Language saved" if lang == LANG_EN else "Язык сохранен")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    lang = _admin_lang(message)
    if lang == LANG_EN:
        text = (
            "Short map:\n\n"
            "Business answers: what we sell, who we write to, and how the manager should behave.\n"
            "Contacts answer: who to write to.\n"
            "Launch connects a business with contacts, shows the first message, and starts outreach.\n"
            "Hot leads and Conversations show people who replied.\n\n"
            "Commands:\n"
            "/start — choose language and open the main menu\n"
            "/cancel — stop the current wizard\n"
            "/back — go one step back in a wizard\n"
            "/help — help\n"
            "/scripts — businesses and messaging setup\n"
            "/newscript — describe a new business\n"
            "/campaigns — launches and statuses\n"
            "/startcampaign — start a saved draft\n"
            "/upload — upload contacts and launch\n"
            "/discover — lead source planner\n"
            "/analytics — analytics\n"
            "/hotleads — hot leads\n"
            "/conversations [query] — recent conversations or search by @username, phone, name, or UUID"
        )
    else:
        text = (
            "Короткая схема:\n\n"
            "Бизнес отвечает на вопрос: что продаем, кому пишем и как должен вести себя менеджер.\n"
            "Контакты отвечают на вопрос: кому писать.\n"
            "Запуск связывает бизнес и контакты, показывает первое сообщение и стартует рассылку.\n"
            "Горячие лиды и диалоги показывают ответы людей.\n\n"
            "Основные команды:\n"
            "/start — выбор языка и главное меню\n"
            "/cancel — отменить текущий мастер настройки\n"
            "/back — шаг назад в мастере настройки\n"
            "/help — помощь\n"
            "/scripts — бизнесы и настройки менеджера\n"
            "/newscript — описать новый бизнес\n"
            "/campaigns — запуски и статусы\n"
            "/startcampaign — запустить сохраненный черновик\n"
            "/upload — загрузить контакты и запустить\n"
            "/discover — план источников лидов\n"
            "/analytics — аналитика\n"
            "/hotleads — горячие лиды\n"
            "/conversations [запрос] — последние диалоги или поиск по @username, телефону, имени или UUID"
        )
    await message.answer(text, reply_markup=_main_menu_keyboard(lang))


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "No active wizard. Choose an action below."
            if lang == LANG_EN
            else "Активного мастера нет. Выберите действие в меню ниже.",
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    await state.clear()
    await message.answer(
        "OK, stopped the current wizard and returned to the main menu."
        if lang == LANG_EN
        else "Ок, остановил текущий мастер. Возвращаю в главное меню.",
        reply_markup=_main_menu_keyboard(lang),
    )


SCRIPT_CREATE_STATE_ORDER: list[State] = [
    ScriptCreateFSM.name,
    ScriptCreateFSM.role_prompt,
    ScriptCreateFSM.target_audience,
    ScriptCreateFSM.goal,
    ScriptCreateFSM.success_criteria,
    ScriptCreateFSM.tone,
    ScriptCreateFSM.sales_strategy,
    ScriptCreateFSM.call_to_action,
    ScriptCreateFSM.follow_up_delay_hours,
    ScriptCreateFSM.working_hours,
    ScriptCreateFSM.timezone,
    ScriptCreateFSM.confirm,
]


def _state_to_name_map() -> dict[str, State]:
    return {state.state: state for state in SCRIPT_CREATE_STATE_ORDER}


def _tone_keyboard(lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    options = TONE_OPTIONS_EN if lang == LANG_EN else TONE_OPTIONS
    rows = [
        [types.InlineKeyboardButton(text=t, callback_data=f"tone:{t}")]
        for t in options
    ]
    rows.append(
        [
            types.InlineKeyboardButton(
                text="← Back" if lang == LANG_EN else "← Назад",
                callback_data="scriptback:tone",
            )
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _strategy_keyboard(lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    rows = []
    for key in ("nurture", "quick_call", "consultative", "qualification"):
        template = SALES_STRATEGY_TEMPLATES[key]
        label = template["label_en"] if lang == LANG_EN else template["label_ru"]
        description = (
            template["description_en"]
            if lang == LANG_EN
            else template["description_ru"]
        )
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{label} · {_compact(description, 34)}",
                    callback_data=f"strategy:{key}",
                )
            ]
        )
    rows.append(
        [
            types.InlineKeyboardButton(
                text="← Back" if lang == LANG_EN else "← Назад",
                callback_data="scriptback:strategy",
            )
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _workhours_keyboard(lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ 09:00-18:00", callback_data="workhours:default"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📝 Enter manually" if lang == LANG_EN else "📝 Указать вручную",
                    callback_data="workhours:manual",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="← Back" if lang == LANG_EN else "← Назад",
                    callback_data="scriptback:workhours",
                )
            ],
        ]
    )


def _script_confirm_keyboard(lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    if lang == LANG_EN:
        labels = {
            "name": "✏️ Name",
            "role": "✏️ Description",
            "aud": "✏️ Audience",
            "goal": "✏️ Goal",
            "crit": "✏️ Success",
            "tone": "✏️ Style",
            "strategy": "✏️ Funnel",
            "cta": "✏️ Next step",
            "follow": "✏️ Follow-up",
            "hours": "✏️ Hours",
            "tz": "✏️ Timezone",
            "save": "✅ Save",
            "cancel": "❌ Cancel",
        }
    else:
        labels = {
            "name": "✏️ Название",
            "role": "✏️ Описание",
            "aud": "✏️ Аудитория",
            "goal": "✏️ Цель",
            "crit": "✏️ Успех",
            "tone": "✏️ Стиль",
            "strategy": "✏️ Воронка",
            "cta": "✏️ Следующий шаг",
            "follow": "✏️ Напоминание",
            "hours": "✏️ Часы",
            "tz": "✏️ Timezone",
            "save": "✅ Сохранить",
            "cancel": "❌ Отмена",
        }
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text=labels["name"], callback_data="sdedit:name"),
                types.InlineKeyboardButton(text=labels["role"], callback_data="sdedit:role"),
            ],
            [
                types.InlineKeyboardButton(text=labels["aud"], callback_data="sdedit:aud"),
                types.InlineKeyboardButton(text=labels["goal"], callback_data="sdedit:goal"),
            ],
            [
                types.InlineKeyboardButton(text=labels["crit"], callback_data="sdedit:crit"),
                types.InlineKeyboardButton(text=labels["tone"], callback_data="sdedit:tone"),
            ],
            [
                types.InlineKeyboardButton(
                    text=labels["strategy"], callback_data="sdedit:strategy"
                ),
                types.InlineKeyboardButton(text=labels["cta"], callback_data="sdedit:cta"),
            ],
            [
                types.InlineKeyboardButton(text=labels["follow"], callback_data="sdedit:follow"),
                types.InlineKeyboardButton(text=labels["hours"], callback_data="sdedit:hours"),
            ],
            [types.InlineKeyboardButton(text=labels["tz"], callback_data="sdedit:tz")],
            [
                types.InlineKeyboardButton(text=labels["save"], callback_data="script:create"),
                types.InlineKeyboardButton(text=labels["cancel"], callback_data="script:cancel"),
            ],
        ]
    )


def _existing_strategy_keyboard(script_id: UUID, lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    rows = []
    for key in ("nurture", "quick_call", "consultative", "qualification"):
        template = SALES_STRATEGY_TEMPLATES[key]
        label = template["label_en"] if lang == LANG_EN else template["label_ru"]
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=label,
                    callback_data=_script_strategy_callback_data(key, script_id),
                )
            ]
        )
    rows.append(
        [
            types.InlineKeyboardButton(
                text="← Back to card" if lang == LANG_EN else "← К карточке",
                callback_data=f"scriptv:{script_id}",
            )
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _script_create_summary(data: dict[str, Any], lang: str = LANG_RU) -> str:
    working_start = data.get("working_hours_start", dt_time(9, 0))
    working_end = data.get("working_hours_end", dt_time(18, 0))
    if lang == LANG_EN:
        return (
            "Review the business before saving.\n\n"
            f"Name: {data.get('name', '—')}\n"
            f"Description: {_compact(data.get('role_prompt'), 600)}\n"
            f"Audience: {_compact(data.get('target_audience'), 300)}\n"
            f"Manager goal: {_compact(data.get('goal'), 300)}\n"
            f"Success: {_compact(data.get('success_criteria'), 300)}\n"
            f"Style: {data.get('tone', 'friendly')}\n"
            f"Sales funnel: {sales_strategy_label(data.get('sales_strategy'), LANG_EN)}\n"
            f"Next step: {data.get('call_to_action', 'short 10-minute call')}\n"
            f"Limit: {data.get('max_messages', 3)} messages per contact\n"
            f"Follow-up: after {data.get('follow_up_delay_hours', 24)} h if no answer\n"
            f"Working hours: {_format_time(working_start)}-{_format_time(working_end)}\n"
            f"Timezone: {data.get('timezone', 'Europe/Moscow')}\n\n"
            "If something is wrong, edit a field with a button below."
        )
    return (
        "Проверьте бизнес перед сохранением.\n\n"
        f"Название: {data.get('name', '—')}\n"
        f"Описание: {_compact(data.get('role_prompt'), 600)}\n"
        f"Аудитория: {_compact(data.get('target_audience'), 300)}\n"
        f"Цель менеджера: {_compact(data.get('goal'), 300)}\n"
        f"Успех: {_compact(data.get('success_criteria'), 300)}\n"
        f"Стиль: {data.get('tone', 'friendly')}\n"
        f"Воронка продаж: {sales_strategy_label(data.get('sales_strategy'), LANG_RU)}\n"
        f"Следующий шаг: {data.get('call_to_action', 'короткий 10-минутный созвон')}\n"
        f"Лимит: {data.get('max_messages', 3)} сообщения на контакт\n"
        f"Напоминание: через {data.get('follow_up_delay_hours', 24)} ч, если нет ответа\n"
        f"Рабочее время: {_format_time(working_start)}-{_format_time(working_end)}\n"
        f"Timezone: {data.get('timezone', 'Europe/Moscow')}\n\n"
        "Если что-то не так, исправьте отдельное поле кнопкой ниже."
    )


async def _send_script_confirm_from_state(
    message: types.Message, state: FSMContext
) -> None:
    lang = _admin_lang(message)
    await state.set_state(ScriptCreateFSM.confirm)
    data = await state.get_data()
    await message.answer(
        _script_create_summary(data, lang),
        reply_markup=_script_confirm_keyboard(lang),
    )


async def _maybe_return_to_script_confirm(
    message: types.Message, state: FSMContext
) -> bool:
    data = await state.get_data()
    if not data.get("_return_to_confirm"):
        return False
    await state.update_data(_return_to_confirm=False, _draft_edit_field=None)
    await _send_script_confirm_from_state(message, state)
    return True


async def _send_script_state_prompt(
    message: types.Message,
    state_obj: State,
    state: FSMContext,
) -> None:
    lang = _admin_lang(message)
    await state.set_state(state_obj)
    state_name = state_obj.state
    if state_name == ScriptCreateFSM.name.state:
        await message.answer(
            "What should we call this business or offer?"
            if lang == LANG_EN
            else "Как назвать этот бизнес или оффер?"
        )
    elif state_name == ScriptCreateFSM.role_prompt.state:
        await message.answer(_script_field_prompt("role_prompt", lang))
    elif state_name == ScriptCreateFSM.target_audience.state:
        await message.answer(_script_field_prompt("target_audience", lang))
    elif state_name == ScriptCreateFSM.goal.state:
        await message.answer(_script_field_prompt("goal", lang))
    elif state_name == ScriptCreateFSM.success_criteria.state:
        await message.answer(_script_field_prompt("success_criteria", lang))
    elif state_name == ScriptCreateFSM.tone.state:
        await message.answer(
            "Choose the communication style:" if lang == LANG_EN else "Выберите стиль общения:",
            reply_markup=_tone_keyboard(lang),
        )
    elif state_name == ScriptCreateFSM.sales_strategy.state:
        await message.answer(
            (
                "Choose the sales funnel.\n\n"
                "This controls how quickly the manager moves from interest to the next step."
            )
            if lang == LANG_EN
            else (
                "Выберите воронку продаж.\n\n"
                "Она управляет тем, как быстро менеджер переходит от интереса к следующему шагу."
            ),
            reply_markup=_strategy_keyboard(lang),
        )
    elif state_name == ScriptCreateFSM.call_to_action.state:
        await message.answer(_script_field_prompt("call_to_action", lang))
    elif state_name == ScriptCreateFSM.follow_up_delay_hours.state:
        await message.answer(_script_field_prompt("follow_up_delay_hours", lang))
    elif state_name == ScriptCreateFSM.working_hours.state:
        await message.answer(
            "When is the manager allowed to send messages?"
            if lang == LANG_EN
            else "Когда менеджеру можно писать?",
            reply_markup=_workhours_keyboard(lang),
        )
    elif state_name == ScriptCreateFSM.timezone.state:
        await message.answer(_script_field_prompt("timezone", lang))
    else:
        await _send_script_confirm_from_state(message, state)


async def _go_script_create_back(message: types.Message, state: FSMContext) -> bool:
    lang = _admin_lang(message)
    current_state = await state.get_state()
    if current_state not in _state_to_name_map():
        await message.answer(
            "Cannot go back from here. Open /start or use /cancel."
            if lang == LANG_EN
            else "Здесь нельзя сделать шаг назад. Откройте /start или /cancel."
        )
        return False
    states = [state_obj.state for state_obj in SCRIPT_CREATE_STATE_ORDER]
    idx = states.index(current_state)
    if idx == 0:
        await message.answer(
            "This is the first step. Continue or use /cancel."
            if lang == LANG_EN
            else "Это первый шаг. Можно продолжить или отменить через /cancel."
        )
        return True
    await _send_script_state_prompt(message, SCRIPT_CREATE_STATE_ORDER[idx - 1], state)
    return True


async def _maybe_handle_back_text(message: types.Message, state: FSMContext) -> bool:
    text = (message.text or "").strip().lower()
    if text not in {"назад", "back", "/back"}:
        return False
    return await _go_script_create_back(message, state)


@router.message(Command("back"))
async def cmd_back(message: types.Message, state: FSMContext):
    if not await _go_script_create_back(message, state):
        lang = _admin_lang(message)
        await message.answer(
            "No active wizard. Open the menu below."
            if lang == LANG_EN
            else "Активного мастера нет. Откройте меню ниже.",
            reply_markup=_main_menu_keyboard(lang),
        )


@router.callback_query(lambda c: c.data and c.data.startswith("scriptback:"))
async def handle_script_back_button(callback: types.CallbackQuery, state: FSMContext):
    if callback.message:
        await _go_script_create_back(callback.message, state)
    await callback.answer()


@router.message(Command("scripts"))
async def cmd_scripts(message: types.Message):
    await _send_or_edit_scripts(message)


async def _load_scripts_with_campaign_counts(limit: int = 10):
    async with AsyncSessionLocal() as session:
        campaign_count = (
            select(func.count(Campaign.id))
            .where(Campaign.script_id == Script.id)
            .scalar_subquery()
        )
        result = await session.execute(
            select(Script, campaign_count).order_by(Script.created_at.desc()).limit(limit)
        )
        return result.all()


async def _send_or_edit_scripts(message: types.Message):
    lang = _admin_lang(message)
    scripts = await _load_scripts_with_campaign_counts()

    if not scripts:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="➕ New business" if lang == LANG_EN else "➕ Описать бизнес",
                        callback_data="script_new",
                    )
                ]
            ]
        )
        text = (
            "No businesses yet. Describe the first business or offer so the manager understands what to sell "
            "and how to talk to leads."
            if lang == LANG_EN
            else "Бизнесов пока нет. Опишите первый бизнес или оффер, чтобы менеджер "
            "понимал, что продает и как общаться с лидами."
        )
        if message.from_user and message.from_user.is_bot:
            try:
                await message.edit_text(text, reply_markup=kb)
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    raise
        else:
            await message.answer(text, reply_markup=kb)
        return

    text = _format_scripts(scripts, lang)
    kb = _build_script_buttons(scripts, lang)
    if message.from_user and message.from_user.is_bot:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as exc:
            error = str(exc).lower()
            if "message is too long" in error:
                text = (
                    "Business list is large. Open a card below to view details."
                    if lang == LANG_EN
                    else "Список бизнесов большой. Откройте карточку ниже, чтобы посмотреть детали."
                )
                await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            elif "message is not modified" not in error:
                raise
    else:
        try:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as exc:
            if "message is too long" not in str(exc).lower():
                raise
            text = (
                "Business list is large. Open a card below to view details."
                if lang == LANG_EN
                else "Список бизнесов большой. Откройте карточку ниже, чтобы посмотреть детали."
            )
            await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "refresh_scripts")
async def refresh_scripts(callback: types.CallbackQuery):
    await cmd_scripts(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "script_new")
async def handle_script_new(callback: types.CallbackQuery, state: FSMContext):
    await cmd_newscript(callback.message, state)
    await callback.answer()


async def _load_script_with_campaign_count(script_id: UUID) -> tuple[Script | None, int]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            return None, 0
        count_result = await session.execute(
            select(func.count(Campaign.id)).where(Campaign.script_id == script_id)
        )
        return script, count_result.scalar() or 0


def _script_detail_keyboard(
    script: Script,
    campaign_count: int = 0,
    lang: str = LANG_RU,
) -> types.InlineKeyboardMarkup:
    if lang == LANG_EN:
        edit_text = "✏️ Edit"
        toggle_text = "⏸ Turn off" if script.is_active else "▶️ Turn on"
        delete_text = "🗑 Delete"
        back_text = "← Back to list"
    else:
        edit_text = "✏️ Редактировать"
        toggle_text = "⏸ Выключить" if script.is_active else "▶️ Включить"
        delete_text = "🗑 Удалить"
        back_text = "← К списку"
    rows = [
        [
            types.InlineKeyboardButton(
                text=edit_text, callback_data=f"scripte:{script.id}"
            )
        ],
        [
            types.InlineKeyboardButton(
                text=toggle_text, callback_data=f"script_toggle:{script.id}"
            ),
            types.InlineKeyboardButton(
                text=delete_text,
                callback_data=f"script_delete:{script.id}:{campaign_count}",
            ),
        ],
        [types.InlineKeyboardButton(text=back_text, callback_data="scripts:list")],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _script_edit_keyboard(script: Script, lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    if lang == LANG_EN:
        labels = {
            "name": "Name",
            "role": "Description",
            "aud": "Audience",
            "goal": "Goal",
            "crit": "Success",
            "tone": "Style",
            "strategy": "Funnel",
            "cta": "Next step",
            "msg": "Limit",
            "follow": "Follow-up",
            "hours": "Hours",
            "tz": "Timezone",
            "back": "← Back to card",
        }
    else:
        labels = {
            "name": "Название",
            "role": "Описание",
            "aud": "Аудитория",
            "goal": "Цель",
            "crit": "Успех",
            "tone": "Стиль",
            "strategy": "Воронка",
            "cta": "Следующий шаг",
            "msg": "Лимит",
            "follow": "Напоминание",
            "hours": "Часы",
            "tz": "Timezone",
            "back": "← К карточке",
        }
    rows = [
        [
            types.InlineKeyboardButton(
                text=labels["name"], callback_data=f"scriptf:name:{script.id}"
            ),
            types.InlineKeyboardButton(
                text=labels["role"], callback_data=f"scriptf:role:{script.id}"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=labels["aud"], callback_data=f"scriptf:aud:{script.id}"
            ),
            types.InlineKeyboardButton(
                text=labels["goal"], callback_data=f"scriptf:goal:{script.id}"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=labels["crit"], callback_data=f"scriptf:crit:{script.id}"
            ),
            types.InlineKeyboardButton(
                text=labels["tone"], callback_data=f"scriptf:tone:{script.id}"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=labels["strategy"], callback_data=f"scriptf:strategy:{script.id}"
            ),
            types.InlineKeyboardButton(
                text=labels["cta"], callback_data=f"scriptf:cta:{script.id}"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=labels["msg"], callback_data=f"scriptf:msg:{script.id}"
            ),
            types.InlineKeyboardButton(
                text=labels["follow"], callback_data=f"scriptf:follow:{script.id}"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=labels["hours"], callback_data=f"scriptf:hours:{script.id}"
            ),
            types.InlineKeyboardButton(
                text=labels["tz"], callback_data=f"scriptf:tz:{script.id}"
            ),
        ],
        [types.InlineKeyboardButton(text=labels["back"], callback_data=f"scriptv:{script.id}")],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(lambda c: c.data == "scripts:list")
async def handle_scripts_list(callback: types.CallbackQuery):
    await _send_or_edit_scripts(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("scriptv:"))
async def handle_script_view(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        script_id = UUID(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    script, campaign_count = await _load_script_with_campaign_count(script_id)
    if not script:
        await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
        return

    await _send_or_edit_callback_message(
        callback,
        _format_script_details(script, campaign_count, lang),
        reply_markup=_script_detail_keyboard(script, campaign_count, lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("scripte:"))
async def handle_script_edit(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        script_id = UUID(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    script, _ = await _load_script_with_campaign_count(script_id)
    if not script:
        await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
        return

    await _send_or_edit_callback_message(
        callback,
        (
            f"What should be changed in <b>{_html(script.name)}</b>?"
            if lang == LANG_EN
            else f"Что изменить в <b>{_html(script.name)}</b>?"
        ),
        reply_markup=_script_edit_keyboard(script, lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("scriptf:"))
async def handle_script_edit_field(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    try:
        _, field_key, script_id_raw = callback.data.split(":", 2)
        field = SCRIPT_FIELD_KEYS[field_key]
        script_id = UUID(script_id_raw)
    except (KeyError, ValueError):
        await callback.answer("❌ Invalid field" if lang == LANG_EN else "❌ Неверное поле")
        return

    script, _ = await _load_script_with_campaign_count(script_id)
    if not script:
        await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
        return

    if field == "sales_strategy":
        await _send_or_edit_callback_message(
            callback,
            (
                f"Choose a sales funnel for <b>{_html(script.name)}</b>."
                if lang == LANG_EN
                else f"Выберите воронку продаж для <b>{_html(script.name)}</b>."
            ),
            reply_markup=_existing_strategy_keyboard(script.id, lang),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await state.set_state(ScriptEditFSM.value)
    await state.update_data(edit_script_id=str(script_id), edit_field=field)
    await _send_or_edit_callback_message(
        callback,
        (
            f"{SCRIPT_FIELD_LABELS_EN.get(field, 'Field')}\n\n{_script_field_prompt(field, lang)}"
            if lang == LANG_EN
            else f"{SCRIPT_FIELD_LABELS.get(field, 'Поле')}\n\n{_script_field_prompt(field, lang)}"
        ),
    )
    await callback.answer()


@router.message(ScriptEditFSM.value)
async def process_script_edit_value(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    data = await state.get_data()
    script_id_raw = data.get("edit_script_id")
    field = data.get("edit_field")
    if not script_id_raw or not field:
        await state.clear()
        await message.answer(
            "The edit session expired. Open /scripts again."
            if lang == LANG_EN
            else "Сессия редактирования устарела. Откройте /scripts заново."
        )
        return

    try:
        script_id = UUID(script_id_raw)
    except ValueError:
        await state.clear()
        await message.answer(
            "Invalid business ID. Open /scripts again."
            if lang == LANG_EN
            else "Неверный ID бизнеса. Откройте /scripts заново."
        )
        return

    raw_value = (message.text or "").strip()
    value: Any = raw_value
    extra_updates: dict[str, Any] = {}
    if field in {"target_audience", "success_criteria"} and raw_value == "-":
        value = None
    elif field in {"name", "role_prompt", "goal", "call_to_action"} and not raw_value:
        await message.answer(
            "This field cannot be empty. Enter text or use /cancel."
            if lang == LANG_EN
            else "Поле не может быть пустым. Введите текст или /cancel."
        )
        return
    elif field == "tone":
        value = TONE_MAP.get(raw_value, raw_value.lower())
        if value not in {"professional", "friendly", "aggressive"}:
            await message.answer(
                "Enter professional, friendly, or aggressive."
                if lang == LANG_EN
                else "Введите professional, friendly или aggressive."
            )
            return
    elif field in {"max_messages", "follow_up_delay_hours"}:
        try:
            value = int(raw_value)
        except ValueError:
            await message.answer("Enter a number." if lang == LANG_EN else "Введите число.")
            return
        if value <= 0:
            await message.answer(
                "The number must be greater than zero."
                if lang == LANG_EN
                else "Число должно быть больше нуля."
            )
            return
    elif field == "timezone":
        value = _resolve_timezone_input(raw_value)
        if value is None:
            await message.answer(
                "I did not understand the timezone. Send something like Europe/Moscow, UTC, or msk."
                if lang == LANG_EN
                else "Не понял часовой пояс. Напишите, например: Europe/Moscow, UTC или msk."
            )
            return
    elif field == "working_hours":
        parsed = _parse_working_hours(raw_value)
        if parsed is None:
            await message.answer(
                "Enter hours as HH:MM-HH:MM, for example 09:00-18:00."
                if lang == LANG_EN
                else "Введите часы в формате HH:MM-HH:MM, например 09:00-18:00."
            )
            return
        extra_updates = {"working_hours_start": parsed[0], "working_hours_end": parsed[1]}

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            await state.clear()
            await message.answer(
                "Business not found. Open /scripts again."
                if lang == LANG_EN
                else "Бизнес не найден. Откройте /scripts заново."
            )
            return
        if field == "working_hours":
            script.working_hours_start = extra_updates["working_hours_start"]
            script.working_hours_end = extra_updates["working_hours_end"]
        else:
            setattr(script, field, value)
        await session.commit()
        await session.refresh(script)

    await state.clear()
    await message.answer(
        (
            "Saved.\n\n" if lang == LANG_EN else "Сохранил.\n\n"
        )
        + _format_script_details(script, lang=lang),
        reply_markup=_script_detail_keyboard(script, lang=lang),
        parse_mode="HTML",
    )


@router.callback_query(
    lambda c: c.data
    and (c.data.startswith("script_strategy:") or c.data.startswith("ss:"))
)
async def handle_script_strategy_update(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        strategy_key, script_id = _parse_script_strategy_callback(callback.data)
    except (KeyError, ValueError, IndexError):
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            await callback.answer(
                "❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден"
            )
            return
        script.sales_funnel = build_sales_funnel(strategy_key)
        await session.commit()
        await session.refresh(script)

    await callback.answer("✅ Saved" if lang == LANG_EN else "✅ Сохранено")
    await _send_or_edit_callback_message(
        callback,
        (
            "Saved.\n\n" if lang == LANG_EN else "Сохранил.\n\n"
        )
        + _format_script_details(script, lang=lang),
        reply_markup=_script_detail_keyboard(script, lang=lang),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data and c.data.startswith("script_toggle:"))
async def handle_script_toggle(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        script_id = UUID(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
            return
        script.is_active = not script.is_active
        await session.commit()

    await callback.answer("✅ Updated" if lang == LANG_EN else "✅ Обновлено")
    await cmd_scripts(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("script_delete:"))
async def handle_script_delete(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        parts = callback.data.split(":")
        script_id = UUID(parts[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        campaign_count_result = await session.execute(
            select(func.count(Campaign.id)).where(Campaign.script_id == script_id)
        )
        campaign_count = campaign_count_result.scalar() or 0
        if campaign_count:
            await callback.answer(
                "❌ This business is used in launches"
                if lang == LANG_EN
                else "❌ Бизнес используется в запусках"
            )
            return

        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
            return
        await session.delete(script)
        await session.commit()

    await callback.answer("🗑 Deleted" if lang == LANG_EN else "🗑 Бизнес удален")
    await cmd_scripts(callback.message)


async def _load_campaigns():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Campaign, Script)
            .join(Script, Campaign.script_id == Script.id, isouter=True)
            .order_by(Campaign.created_at.desc())
            .limit(20)
        )
        return result.all()


async def _send_or_edit_campaigns(message: types.Message):
    lang = _admin_lang(message)
    campaigns = await _load_campaigns()

    if not campaigns:
        text = (
            "No launches yet.\n\n"
            "Open Contacts & launch, upload a file, choose a business, review the first message, "
            "and start outreach."
            if lang == LANG_EN
            else
            "Запусков пока нет.\n\n"
            "Загрузите контакты через «Контакты и запуск», выберите бизнес, "
            "проверьте первое сообщение и запустите отправку."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=[])
    else:
        text = _format_campaigns(campaigns, lang)
        kb_rows = []
        for row in campaigns:
            campaign = row[0]
            kb_rows.append(_build_campaign_buttons(campaign, lang))
        kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)

    if message.from_user and message.from_user.is_bot:
        # Editing the bot's own message (e.g. after a callback button click)
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as exc:
            # Ignore "message is not modified" and similar edit errors;
            # do not send a duplicate message.
            if "message is not modified" not in str(exc).lower():
                raise
    else:
        # User-sent command message: send a new message instead of editing.
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("campaigns"))
async def cmd_campaigns(message: types.Message):
    await _send_or_edit_campaigns(message)


@router.callback_query(lambda c: c.data and c.data.startswith("camp_pause:"))
async def handle_camp_pause(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if campaign and campaign.status == "running":
            campaign.status = "paused"
            await session.commit()
            await callback.answer("⏸ Paused" if lang == LANG_EN else "⏸ Пауза")
        else:
            await callback.answer(
                "❌ Cannot pause this launch"
                if lang == LANG_EN
                else "❌ Нельзя поставить на паузу"
            )
    await _send_or_edit_campaigns(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("camp_resume:"))
async def handle_camp_resume(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if campaign and campaign.status == "paused":
            campaign.status = "running"
            await session.commit()
            await callback.answer("▶️ Resumed" if lang == LANG_EN else "▶️ Возобновлено")
        else:
            await callback.answer(
                "❌ Cannot resume this launch"
                if lang == LANG_EN
                else "❌ Нельзя возобновить"
            )
    await _send_or_edit_campaigns(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("camp_start:"))
async def handle_camp_start(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    camp_id_str = callback.data.split(":", 1)[1]
    started_total_contacts: int | None = None
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        script = None
        if campaign and campaign.status == "draft":
            script_result = await session.execute(
                select(Script).where(Script.id == campaign.script_id)
            )
            script_candidate = script_result.scalar_one_or_none()
            script = script_candidate if isinstance(script_candidate, Script) else None
            campaign.status = "running"
            campaign.started_at = datetime.now(timezone.utc)
            await session.commit()
            await callback.answer("▶️ Started" if lang == LANG_EN else "▶️ Запущено")
            started_total_contacts = campaign.total_contacts or 0
            from app.core.scheduler import process_campaigns

            _schedule_process_campaign(campaign.id, process_campaigns)
        else:
            await callback.answer(
                "❌ Launch already started or not found"
                if lang == LANG_EN
                else "❌ Запуск уже начат или не найден"
            )
    await _send_or_edit_campaigns(callback.message)
    if started_total_contacts and callback.message:
        notice = _launch_queue_notice(
            started_total_contacts,
            lang,
        ) + _launch_timing_notice(script, lang)
        await callback.message.answer(notice.strip())


@router.callback_query(lambda c: c.data and c.data.startswith("camp_delete:"))
async def handle_camp_delete(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if campaign:
            # Delete dependent records in the right order to avoid FK violations:
            # messages -> conversations -> campaign_contacts -> campaign
            conv_ids_result = await session.execute(
                select(Conversation.id).where(Conversation.campaign_id == camp_id)
            )
            conv_ids = [row[0] for row in conv_ids_result.all()]
            if conv_ids:
                await session.execute(
                    delete(Message).where(Message.conversation_id.in_(conv_ids))
                )
                await session.execute(
                    delete(Conversation).where(Conversation.campaign_id == camp_id)
                )
            await session.execute(
                delete(CampaignContact).where(CampaignContact.campaign_id == camp_id)
            )
            await session.delete(campaign)
            await session.commit()
            await callback.answer("🗑 Deleted" if lang == LANG_EN else "🗑 Удалено")
        else:
            await callback.answer("❌ Launch not found" if lang == LANG_EN else "❌ Запуск не найден")
    await _send_or_edit_campaigns(callback.message)


@router.message(Command("analytics"))
async def cmd_analytics(message: types.Message):
    lang = _admin_lang(message)
    async with AsyncSessionLocal() as session:
        total_contacts = await session.scalar(select(func.count(Contact.id)))
        sent = await session.scalar(
            select(func.count(Message.id)).where(Message.direction == "outbound")
        )
        replied = await session.scalar(
            select(func.count(Message.id)).where(Message.direction == "inbound")
        )
        hot = await session.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.current_state == "hot"
            )
        )
        meetings = await session.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.current_state == "meeting_booked"
            )
        )
        rejected = await session.scalar(
            select(func.count(Message.id))
            .where(Message.direction == "outbound")
            .where(Message.llm_model == "fallback")
        )
        avg_length = await session.scalar(
            select(func.coalesce(func.avg(func.length(Message.content)), 0)).where(
                Message.direction == "outbound"
            )
        )

    text = _format_analytics(
        total_contacts or 0,
        sent or 0,
        replied or 0,
        hot or 0,
        meetings or 0,
        rejected or 0,
        avg_length or 0.0,
        lang,
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📋 Export CSV" if lang == LANG_EN else "📋 Экспорт в CSV",
                    callback_data="export_analytics",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🔄 Refresh" if lang == LANG_EN else "🔄 Обновить",
                    callback_data="refresh_analytics",
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data == "refresh_analytics")
async def refresh_analytics(callback: types.CallbackQuery):
    await cmd_analytics(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "export_analytics")
async def export_analytics(callback: types.CallbackQuery):
    import csv
    import io
    lang = _admin_lang(callback)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Contact, Campaign, CampaignContact)
            .join(CampaignContact, CampaignContact.contact_id == Contact.id)
            .join(Campaign, Campaign.id == CampaignContact.campaign_id)
        )
        rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "contact_id",
            "username",
            "first_name",
            "last_name",
            "company",
            "position",
            "campaign",
            "campaign_status",
            "contact_status",
        ]
    )
    for contact, campaign, cc in rows:
        writer.writerow(
            [
                str(contact.id),
                contact.telegram_username,
                contact.first_name,
                contact.last_name,
                contact.company_name,
                contact.position,
                campaign.name,
                campaign.status,
                cc.status,
            ]
        )

    bytes_output = io.BytesIO(output.getvalue().encode("utf-8"))
    bytes_output.seek(0)
    bot = _get_bot()
    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=types.BufferedInputFile(bytes_output.read(), filename="analytics.csv"),
        caption="📋 Launch analytics" if lang == LANG_EN else "📋 Аналитика по запускам",
    )
    await callback.answer("📋 File sent" if lang == LANG_EN else "📋 Файл отправлен")


@router.message(Command("hotleads"))
async def cmd_hotleads(message: types.Message):
    await _send_hotleads_overview(message, _admin_lang(message))


async def _load_hotleads(limit: int = 20):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation, Contact)
            .join(Contact, Conversation.contact_id == Contact.id)
            .where(Conversation.current_state.in_(["hot", "meeting_booked"]))
            .order_by(Conversation.last_message_at.desc())
            .limit(20)
        )
        return result.all()


async def _send_hotleads_overview(message: types.Message, lang: str = LANG_RU):
    rows = await _load_hotleads()
    if not rows:
        text = (
            "No hot leads yet.\n\n"
            "When a lead shows interest or agrees to a meeting, they will appear here."
            if lang == LANG_EN
            else "Горячих лидов пока нет.\n\n"
            "Когда лид проявит интерес или согласится на встречу, он появится здесь."
        )
        await message.answer(
            text,
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    header = (
        "Hot leads. Open a card to see the conversation and mark the outcome."
        if lang == LANG_EN
        else "Горячие лиды. Откройте карточку, чтобы посмотреть диалог и поставить ручную отметку."
    )
    await message.answer(
        header + "\n\n" + _format_hotleads(rows, lang),
        reply_markup=_hotlead_overview_keyboard(rows, lang),
        parse_mode="HTML",
    )


async def _edit_hotleads_overview(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    rows = await _load_hotleads()
    if not rows:
        text = "No hot leads yet." if lang == LANG_EN else "Горячих лидов пока нет."
        await _send_or_edit_callback_message(
            callback,
            text,
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="🔄 Refresh" if lang == LANG_EN else "🔄 Обновить",
                            callback_data="refresh_hotleads",
                        )
                    ]
                ]
            ),
        )
        return
    header = (
        "Hot leads. Open a card to see the conversation and mark the outcome."
        if lang == LANG_EN
        else "Горячие лиды. Откройте карточку, чтобы посмотреть диалог и поставить ручную отметку."
    )
    await _send_or_edit_callback_message(
        callback,
        header + "\n\n" + _format_hotleads(rows, lang),
        reply_markup=_hotlead_overview_keyboard(rows, lang),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "refresh_hotleads")
async def refresh_hotleads(callback: types.CallbackQuery):
    await _edit_hotleads_overview(callback)
    await callback.answer()


@router.callback_query(lambda c: c.data == "hotleads:list")
async def handle_hotleads_list(callback: types.CallbackQuery):
    await _edit_hotleads_overview(callback)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("lead:"))
async def handle_hotlead_card(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        conv_id = UUID(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid conversation ID" if lang == LANG_EN else "❌ Неверный ID диалога")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation, Contact)
            .join(Contact, Conversation.contact_id == Contact.id)
            .where(Conversation.id == conv_id)
        )
        row = result.first()

    if not row:
        await callback.answer("❌ Conversation not found" if lang == LANG_EN else "❌ Диалог не найден")
        return

    conv, contact = row
    await _send_or_edit_callback_message(
        callback,
        _format_hotlead_detail(conv, contact, lang),
        reply_markup=_hotlead_detail_keyboard(conv.id, lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("qualify:"))
async def handle_qualify(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    conv_id_str = callback.data.split(":", 1)[1]
    try:
        conv_id = UUID(conv_id_str)
    except ValueError:
        await callback.answer("❌ Invalid conversation ID" if lang == LANG_EN else "❌ Неверный ID диалога")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.operator_status = "qualified"
            await session.commit()
            if lang == LANG_EN:
                await callback.answer("✅ Marked as qualified")
            else:
                await callback.answer("✅ Отмечено: готов к работе")
        else:
            await callback.answer("❌ Conversation not found" if lang == LANG_EN else "❌ Диалог не найден")


@router.callback_query(lambda c: c.data and c.data.startswith("reject:"))
async def handle_reject(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    conv_id_str = callback.data.split(":", 1)[1]
    try:
        conv_id = UUID(conv_id_str)
    except ValueError:
        await callback.answer("❌ Invalid conversation ID" if lang == LANG_EN else "❌ Неверный ID диалога")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.operator_status = "rejected"
            await session.commit()
            if lang == LANG_EN:
                await callback.answer("🚫 Marked as not a fit")
            else:
                await callback.answer("🚫 Отмечено: не целевой")
        else:
            await callback.answer("❌ Conversation not found" if lang == LANG_EN else "❌ Диалог не найден")


@router.callback_query(lambda c: c.data and c.data.startswith("dialog:"))
async def handle_dialog(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    conv_id_str = callback.data.split(":", 1)[1]
    try:
        conv_id = UUID(conv_id_str)
    except ValueError:
        await callback.answer("❌ Invalid conversation ID" if lang == LANG_EN else "❌ Неверный ID диалога")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.sent_at.desc())
            .limit(10)
        )
        messages = list(reversed(result.scalars().all()))

    if not messages:
        await callback.message.answer(
            "No messages found in this conversation."
            if lang == LANG_EN
            else "Сообщений в диалоге не найдено."
        )
        await callback.answer()
        return

    lines = []
    for msg in messages:
        sender = "👤" if msg.direction == "inbound" else "🤖"
        lines.append(f"{sender} {msg.content}")

    text = "\n\n".join(lines)
    await callback.message.answer(
        text,
        reply_markup=_history_collapse_keyboard(conv_id, lang),
    )
    await callback.answer()


def _format_history_messages(messages: List[Message], limit: int = 20) -> str:
    lines = []
    for msg in messages[-limit:]:
        sender = "👤" if msg.direction == "inbound" else "🤖"
        ts = msg.sent_at
        if ts:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts = ts.astimezone(timezone.utc)
            ts_str = ts.strftime("%H:%M %d.%m")
        else:
            ts_str = "--:--"
        lines.append(f"{ts_str} {sender}\n{msg.content}")
    return "\n\n".join(lines)


def _parse_history_callback_data(data: str, prefix: str) -> tuple[UUID, str]:
    parts = data.split(":")
    expected_prefixes = {prefix}
    if prefix == "history_collapse":
        expected_prefixes.add("hc")
    if len(parts) < 2 or parts[0] not in expected_prefixes:
        raise ValueError("invalid history callback")
    origin = parts[2] if len(parts) > 2 else "message"
    if parts[0] == "hc":
        origin = HISTORY_ORIGIN_CALLBACK_CODES.get(origin, origin)
    return UUID(parts[1]), origin


def _history_collapse_keyboard(
    conv_id: UUID,
    lang: str = LANG_RU,
    origin: str = "message",
) -> types.InlineKeyboardMarkup:
    text = "▾ Collapse conversation" if lang == LANG_EN else "▾ Свернуть диалог"
    origin_code = HISTORY_ORIGIN_CALLBACK_KEYS.get(origin, "m")
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=text,
                    callback_data=f"hc:{conv_id}:{origin_code}",
                )
            ]
        ]
    )


def _history_open_keyboard(conv_id: UUID, lang: str = LANG_RU) -> types.InlineKeyboardMarkup:
    text = "📜 Open conversation" if lang == LANG_EN else "📜 Открыть диалог"
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=text,
                    callback_data=f"history:{conv_id}",
                )
            ]
        ]
    )


def _split_long_text(text: str, max_len: int = 3800) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = block[:max_len]
    if current:
        chunks.append(current)
    return chunks or [text[:max_len]]


@router.callback_query(lambda c: c.data and c.data.startswith("history:"))
async def handle_history(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        conv_id, origin = _parse_history_callback_data(callback.data, "history")
    except ValueError:
        await callback.answer("❌ Invalid conversation ID" if lang == LANG_EN else "❌ Неверный ID диалога")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.sent_at.desc())
            .limit(20)
        )
        messages = list(reversed(result.scalars().all()))

    if not messages:
        await callback.message.answer(
            "No messages found in this conversation."
            if lang == LANG_EN
            else "Сообщений в диалоге не найдено."
        )
        await callback.answer()
        return

    text = _format_history_messages(messages)
    chunks = _split_long_text(text)
    for idx, chunk in enumerate(chunks):
        await callback.message.answer(
            chunk,
            reply_markup=_history_collapse_keyboard(conv_id, lang, origin)
            if idx == len(chunks) - 1
            else None,
        )
    await callback.answer()


@router.callback_query(
    lambda c: c.data
    and (c.data.startswith("history_collapse:") or c.data.startswith("hc:"))
)
async def handle_history_collapse(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    try:
        _parse_history_callback_data(callback.data, "history_collapse")
    except ValueError:
        await callback.answer("❌ Invalid conversation ID" if lang == LANG_EN else "❌ Неверный ID диалога")
        return

    try:
        await callback.message.delete()
    except TelegramBadRequest as exc:
        logger.debug("Could not delete history message while collapsing: %s", exc)
    await callback.answer()


@router.message(Command("conversations"))
async def cmd_conversations(message: types.Message):
    lang = _admin_lang(message)
    raw_text = (message.text or "").strip()
    menu_texts = {
        MENU_CONVERSATIONS,
        MENU_CONVERSATIONS_EN,
        "Conversations",
    }
    args = raw_text.split(maxsplit=1)
    if raw_text in menu_texts:
        args = [raw_text]
    if len(args) < 2:
        await _send_recent_conversations(message, lang)
        return

    query = args[1].strip()
    conversation_id = await _find_conversation_id_by_query(query)
    if conversation_id is None:
        text = (
            "I could not find a conversation for that query.\n\n"
            "Open /conversations and use a button, or search by @username, phone, name, company, contact UUID, "
            "or conversation UUID."
            if lang == LANG_EN
            else "Не нашел диалог по этому запросу.\n\n"
            "Откройте /conversations и нажмите кнопку, либо ищите по @username, телефону, имени, компании, "
            "UUID контакта или UUID диалога."
        )
        await message.answer(text, reply_markup=_main_menu_keyboard(lang))
        return

    await _send_conversation_history(message, conversation_id, lang)


async def _find_conversation_id_by_query(query: str) -> UUID | None:
    raw = query.strip()
    normalized = raw.lstrip("@").lower()
    async with AsyncSessionLocal() as session:
        uuid_value: UUID | None = None
        try:
            uuid_value = UUID(raw)
        except ValueError:
            uuid_value = None

        if uuid_value is not None:
            result = await session.execute(
                select(Conversation.id)
                .join(Contact, Conversation.contact_id == Contact.id)
                .where(or_(Conversation.id == uuid_value, Contact.id == uuid_value))
                .order_by(Conversation.last_message_at.desc().nullslast())
                .limit(1)
            )
            found = result.scalar_one_or_none()
            if found:
                return _conversation_id_from_row(found)

        like_query = f"%{normalized}%"
        result = await session.execute(
            select(Conversation.id)
            .join(Contact, Conversation.contact_id == Contact.id)
            .where(
                or_(
                    func.lower(Contact.telegram_username).like(like_query),
                    Contact.phone.ilike(f"%{raw}%"),
                    func.lower(Contact.first_name).like(like_query),
                    func.lower(Contact.last_name).like(like_query),
                    func.lower(Contact.company_name).like(like_query),
                )
            )
            .order_by(Conversation.last_message_at.desc().nullslast())
            .limit(1)
        )
        return _conversation_id_from_row(result.scalar_one_or_none())


async def _load_conversation_messages(conversation_id: UUID, limit: int = 50) -> list[Message]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sent_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def _send_conversation_history(message: types.Message, conversation_id: UUID, lang: str = LANG_RU):
    messages = await _load_conversation_messages(conversation_id)
    if not messages:
        await message.answer(
            "No messages in this conversation yet." if lang == LANG_EN else "В диалоге пока нет сообщений."
        )
        return

    text = _format_history_messages(messages)
    chunks = _split_long_text(text)
    for idx, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            reply_markup=_history_collapse_keyboard(conversation_id, lang, "conversations")
            if idx == len(chunks) - 1
            else None,
        )


async def _send_recent_conversations(message: types.Message, lang: str = LANG_RU):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation, Contact)
            .join(Contact, Conversation.contact_id == Contact.id)
            .order_by(Conversation.last_message_at.desc())
            .limit(10)
        )
        rows = result.all()

    if not rows:
        text = (
            "No conversations yet.\n\n"
            "They will appear here when leads start replying."
            if lang == LANG_EN
            else "Диалогов пока нет.\n\n"
            "Они появятся здесь, когда лиды начнут отвечать."
        )
        await message.answer(text, reply_markup=_main_menu_keyboard(lang))
        return

    lines = []
    kb_rows = []
    for idx, (conversation, contact) in enumerate(rows, 1):
        name = _contact_display_name(contact)
        status = _state_label(conversation.current_state, lang)
        lines.append(
            f"{idx}. <b>{name}</b>\n"
            f"{'Status' if lang == LANG_EN else 'Статус'}: {status}\n"
            f"contact_id: <code>{contact.id}</code>"
        )
        kb_rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"📜 {'Open' if lang == LANG_EN else 'Открыть'} {idx}",
                    callback_data=f"history:{conversation.id}:conversations",
                )
            ]
        )

    title = "Recent conversations:" if lang == LANG_EN else "Последние диалоги:"
    await message.answer(
        title + "\n\n" + "\n\n".join(lines),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM: Create Script
# ---------------------------------------------------------------------------


@router.message(Command("newscript"))
async def cmd_newscript(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    await state.set_state(ScriptCreateFSM.name)
    await message.answer(
        (
            "Let's describe the business the manager will represent.\n\n"
            "Step 1: name. What should we call this business or offer?\n"
            "Example: Branded cups for coffee shops."
        )
        if lang == LANG_EN
        else (
            "Опишем бизнес, для которого AI-менеджер будет писать лидам.\n\n"
            "Шаг 1: название. Как назвать этот бизнес или оффер?\n"
            "Например: «Стаканчики для кофеен»."
        )
    )


@router.message(ScriptCreateFSM.name)
async def process_script_name(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    if not (message.text or "").strip():
        await message.answer("Name cannot be empty." if lang == LANG_EN else "Название не может быть пустым.")
        return
    await state.update_data(name=message.text)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.role_prompt)
    await message.answer(
        (
            "Step 2: business description.\n\n"
            "What do you sell, who do you help, and why is it useful? "
            "This is the main context for the model, so 2-5 concrete sentences work best."
        )
        if lang == LANG_EN
        else (
            "Шаг 2: описание бизнеса.\n\n"
            "Что продаете, кому помогаете, почему это полезно? "
            "Это главный контекст для модели, поэтому лучше 2-5 живых предложений."
        )
    )


@router.message(ScriptCreateFSM.role_prompt)
async def process_script_role(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    if not (message.text or "").strip():
        await message.answer(
            "Business description cannot be empty."
            if lang == LANG_EN
            else "Описание бизнеса не может быть пустым."
        )
        return
    await state.update_data(role_prompt=message.text)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.target_audience)
    await message.answer(
        (
            "Step 3: audience.\n\n"
            "Example: coffee shop owners, procurement managers, HoReCa, small chains. "
            "Send '-' if you want to fill this later."
        )
        if lang == LANG_EN
        else (
            "Шаг 3: аудитория.\n\n"
            "Например: владельцы кофеен, закупщики, HoReCa, небольшие сети. "
            "Можно отправить '-', если аудиторию опишете позже."
        )
    )


@router.message(ScriptCreateFSM.target_audience)
async def process_script_audience(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    text = message.text.strip()
    await state.update_data(target_audience=None if text == "-" else text)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.goal)
    await message.answer(
        (
            "Step 4: conversation goal.\n\n"
            "Usually: spark interest, answer questions, and gently offer a short call."
        )
        if lang == LANG_EN
        else (
            "Шаг 4: цель переписки.\n\n"
            "Обычно: заинтересовать, ответить на вопросы и мягко предложить короткий созвон."
        )
    )


@router.message(ScriptCreateFSM.goal)
async def process_script_goal(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    if not (message.text or "").strip():
        await message.answer("Goal cannot be empty." if lang == LANG_EN else "Цель не может быть пустой.")
        return
    await state.update_data(goal=message.text)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.success_criteria)
    await message.answer(
        (
            "Step 5: success criteria.\n\n"
            "Example: the lead agreed to a 10-minute call, asked for a proposal, or shared a decision-maker contact. "
            "Send '-' to leave empty."
        )
        if lang == LANG_EN
        else (
            "Шаг 5: критерий успеха.\n\n"
            "Например: лид согласился на 10-минутный созвон, попросил КП или дал контакт ЛПР. "
            "Можно отправить '-'."
        )
    )


@router.message(ScriptCreateFSM.success_criteria)
async def process_script_criteria(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    text = message.text.strip()
    await state.update_data(success_criteria=None if text == "-" else text)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.tone)
    await message.answer(
        "Step 6: communication style."
        if lang == LANG_EN
        else "Шаг 6: стиль общения.",
        reply_markup=_tone_keyboard(lang),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("tone:"))
async def process_script_tone(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    tone_label = callback.data.split(":", 1)[1]
    tone_value = TONE_MAP.get(tone_label, "professional")
    await state.update_data(
        tone=tone_value,
        first_message_goal="trust",
        language=lang,
        emoji_policy="forbidden",
        max_first_message_length=240,
        max_messages=3,
    )
    if await _maybe_return_to_script_confirm(callback.message, state):
        await callback.answer()
        return
    await state.set_state(ScriptCreateFSM.sales_strategy)
    await callback.message.answer(
        (
            "Step 7: sales funnel.\n\n"
            "Choose how the manager should sell: slow nurture, quick call, "
            "consultative, or decision-maker qualification."
        )
        if lang == LANG_EN
        else (
            "Шаг 7: воронка продаж.\n\n"
            "Выберите, как менеджер должен продавать: бережно прогревать, "
            "быстро вести к созвону, консультировать или квалифицировать ЛПР."
        )
        ,
        reply_markup=_strategy_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("strategy:"))
async def process_script_strategy(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    strategy_key = normalize_sales_strategy(callback.data.split(":", 1)[1])
    await state.update_data(
        sales_strategy=strategy_key,
        sales_funnel=build_sales_funnel(strategy_key),
    )
    if await _maybe_return_to_script_confirm(callback.message, state):
        await callback.answer()
        return
    await state.set_state(ScriptCreateFSM.call_to_action)
    await callback.message.answer(
        (
            "Step 8: next step.\n\n"
            "What should the manager offer when the lead is ready? "
            "Example: a short 10-minute call to understand the task and answer questions."
        )
        if lang == LANG_EN
        else (
            "Шаг 8: следующий шаг.\n\n"
            "Что менеджер должен предложить, когда лид готов? "
            "Например: «короткий 10-минутный созвон, чтобы понять задачу и ответить на вопросы»."
        )
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("fmg:"))
async def process_script_first_message_goal(
    callback: types.CallbackQuery, state: FSMContext
):
    goal = callback.data.split(":", 1)[1]
    await state.update_data(first_message_goal=goal)
    await state.set_state(ScriptCreateFSM.call_to_action)
    await callback.message.answer(
        "Введите призыв к действию (call_to_action), например:\n'15-минутный созвон'"
    )
    await callback.answer()


@router.message(ScriptCreateFSM.call_to_action)
async def process_script_call_to_action(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    if not (message.text or "").strip():
        await message.answer(
            "Next step cannot be empty." if lang == LANG_EN else "Следующий шаг не может быть пустым."
        )
        return
    await state.update_data(call_to_action=message.text)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.follow_up_delay_hours)
    await message.answer(
        (
            "Step 9: follow-up delay.\n\n"
            "Usually 24. The follow-up will be soft, without pressure."
        )
        if lang == LANG_EN
        else (
            "Шаг 9: напоминание.\n\n"
            "Обычно 24. Напоминание будет мягким, без давления."
        )
    )


@router.message(ScriptCreateFSM.language)
async def process_script_language(message: types.Message, state: FSMContext):
    lang = message.text.strip().lower()
    if lang not in ("ru", "en"):
        lang = "ru"
    await state.update_data(language=lang)
    await state.set_state(ScriptCreateFSM.emoji_policy)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Forbidden" if lang == LANG_EN else "Запрещены",
                    callback_data="emoji:forbidden",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Rarely" if lang == LANG_EN else "Редко",
                    callback_data="emoji:rare",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Allowed" if lang == LANG_EN else "Разрешены",
                    callback_data="emoji:allowed",
                )
            ],
        ]
    )
    await message.answer(
        "Emoji policy:" if lang == LANG_EN else "Политика использования эмодзи:",
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("emoji:"))
async def process_script_emoji_policy(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    policy = callback.data.split(":", 1)[1]
    await state.update_data(emoji_policy=policy)
    await state.set_state(ScriptCreateFSM.max_first_message_length)
    await callback.message.answer(
        "Enter the maximum first-message length in characters, for example 200:"
        if lang == LANG_EN
        else "Введите максимальную длину первого сообщения в символах (например, 200):"
    )
    await callback.answer()


@router.message(ScriptCreateFSM.max_first_message_length)
async def process_script_max_first_message_length(
    message: types.Message, state: FSMContext
):
    lang = _admin_lang(message)
    try:
        val = int(message.text)
    except ValueError:
        await message.answer("❌ Enter a number." if lang == LANG_EN else "❌ Введите число.")
        return
    await state.update_data(max_first_message_length=val)
    await state.set_state(ScriptCreateFSM.max_messages)
    await message.answer(
        "Enter the maximum number of messages per contact, for example 2:"
        if lang == LANG_EN
        else "Введите максимальное количество сообщений на контакт (например, 2):"
    )


@router.message(ScriptCreateFSM.max_messages)
async def process_script_max_messages(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    try:
        val = int(message.text)
    except ValueError:
        await message.answer("❌ Enter a number." if lang == LANG_EN else "❌ Введите число.")
        return
    await state.update_data(max_messages=val)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.follow_up_delay_hours)
    await message.answer(_script_field_prompt("follow_up_delay_hours", lang))


@router.message(ScriptCreateFSM.follow_up_delay_hours)
async def process_script_delay(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    try:
        val = int(message.text)
    except ValueError:
        await message.answer("❌ Enter a number." if lang == LANG_EN else "❌ Введите число.")
        return
    if val <= 0:
        await message.answer("Enter a number greater than zero." if lang == LANG_EN else "Введите число больше нуля.")
        return
    await state.update_data(follow_up_delay_hours=val)
    if await _maybe_return_to_script_confirm(message, state):
        return
    await state.set_state(ScriptCreateFSM.working_hours)
    await message.answer(
        "Step 10: working hours. When is the manager allowed to send messages? Default is 09:00-18:00."
        if lang == LANG_EN
        else "Шаг 10: рабочее время. Когда менеджеру можно писать? По умолчанию 09:00-18:00.",
        reply_markup=_workhours_keyboard(lang),
    )


@router.callback_query(lambda c: c.data == "workhours:default")
async def process_work_hours_default(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    await state.update_data(working_hours_start=dt_time(9, 0))
    await state.update_data(working_hours_end=dt_time(18, 0))
    if await _maybe_return_to_script_confirm(callback.message, state):
        await callback.answer()
        return
    await state.set_state(ScriptCreateFSM.timezone)
    await callback.message.answer(
        (
            "Enter timezone.\n\n"
            "Examples: Europe/Moscow, UTC, msk. If the value is unclear, I will ask you to fix it."
        )
        if lang == LANG_EN
        else (
            "Введите часовой пояс.\n\n"
            "Примеры: Europe/Moscow, UTC, msk. Если напишете непонятное значение, я попрошу исправить."
        )
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "workhours:manual")
async def process_work_hours_manual(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    await state.set_state(ScriptCreateFSM.working_hours)
    await callback.message.answer(
        "Enter working hours as HH:MM-HH:MM, for example 09:00-18:00:"
        if lang == LANG_EN
        else "Введите рабочие часы в формате HH:MM-HH:MM, например 09:00-18:00:"
    )
    await callback.answer()


@router.message(ScriptCreateFSM.working_hours)
async def process_script_work_start(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    try:
        parts = message.text.split("-")
        if len(parts) == 2:
            start_str, end_str = parts[0].strip(), parts[1].strip()
            h1, m1 = map(int, start_str.split(":"))
            h2, m2 = map(int, end_str.split(":"))
            await state.update_data(working_hours_start=dt_time(h1, m1))
            await state.update_data(working_hours_end=dt_time(h2, m2))
            if await _maybe_return_to_script_confirm(message, state):
                return
            await state.set_state(ScriptCreateFSM.timezone)
            await message.answer(
                (
                    "Enter timezone.\n\n"
                    "Examples: Europe/Moscow, UTC, msk. I will not save an unclear value."
                )
                if lang == LANG_EN
                else (
                    "Введите часовой пояс.\n\n"
                    "Примеры: Europe/Moscow, UTC, msk. Непонятное значение не сохраню."
                )
            )
        else:
            start_str = message.text.strip()
            h1, m1 = map(int, start_str.split(":"))
            dt_time(h1, m1)
            await state.update_data(_start_tmp=start_str)
            await state.set_state(ScriptCreateFSM.working_hours_end)
            await message.answer(
                "Enter end of working hours (HH:MM, for example 18:00):"
                if lang == LANG_EN
                else "Введите конец рабочих часов (HH:MM, например 18:00):"
            )
    except ValueError:
        await message.answer(
            "❌ Invalid format. Enter HH:MM-HH:MM or two separate values."
            if lang == LANG_EN
            else "❌ Неверный формат. Введите HH:MM-HH:MM или два отдельных значения."
        )


@router.message(ScriptCreateFSM.working_hours_end)
async def process_script_work_end(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    try:
        data = await state.get_data()
        start_str = data.get("_start_tmp")
        end_str = message.text.strip()
        h1, m1 = map(int, start_str.split(":"))
        h2, m2 = map(int, end_str.split(":"))
        await state.update_data(working_hours_start=dt_time(h1, m1))
        await state.update_data(working_hours_end=dt_time(h2, m2))
        if await _maybe_return_to_script_confirm(message, state):
            return
        await state.set_state(ScriptCreateFSM.timezone)
        await message.answer(
            "Enter timezone, for example Europe/Moscow, UTC, or msk:"
            if lang == LANG_EN
            else "Введите часовой пояс, например Europe/Moscow, UTC или msk:"
        )
    except ValueError:
        await message.answer(
            "❌ Invalid format. Enter time as HH:MM."
            if lang == LANG_EN
            else "❌ Неверный формат. Введите время в формате HH:MM."
        )


@router.message(ScriptCreateFSM.timezone)
async def process_script_timezone(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if await _maybe_handle_back_text(message, state):
        return
    tz = _resolve_timezone_input(message.text.strip() or "Europe/Moscow")
    if tz is None:
        await message.answer(
            (
                "I did not understand the timezone and will not save a random value.\n\n"
                "Send something like Europe/Moscow, UTC, or msk."
            )
            if lang == LANG_EN
            else (
                "Не понял часовой пояс и не буду сохранять случайное значение.\n\n"
                "Напишите, например: Europe/Moscow, UTC или msk."
            )
        )
        return
    await state.update_data(timezone=tz)
    await _send_script_confirm_from_state(message, state)


@router.callback_query(lambda c: c.data and c.data.startswith("sdedit:"))
async def handle_script_draft_edit(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    try:
        field_key = callback.data.split(":", 1)[1]
        field = SCRIPT_FIELD_KEYS[field_key]
    except (IndexError, KeyError):
        await callback.answer("❌ Invalid field" if lang == LANG_EN else "❌ Неверное поле")
        return

    await state.update_data(_return_to_confirm=True, _draft_edit_field=field)
    if field == "working_hours":
        await state.set_state(ScriptCreateFSM.working_hours)
    elif field == "sales_strategy":
        await state.set_state(ScriptCreateFSM.sales_strategy)
    else:
        state_by_field = {
            "name": ScriptCreateFSM.name,
            "role_prompt": ScriptCreateFSM.role_prompt,
            "target_audience": ScriptCreateFSM.target_audience,
            "goal": ScriptCreateFSM.goal,
            "success_criteria": ScriptCreateFSM.success_criteria,
            "tone": ScriptCreateFSM.tone,
            "call_to_action": ScriptCreateFSM.call_to_action,
            "follow_up_delay_hours": ScriptCreateFSM.follow_up_delay_hours,
            "timezone": ScriptCreateFSM.timezone,
        }
        await state.set_state(state_by_field.get(field, ScriptCreateFSM.confirm))

    if field == "tone":
        await _send_or_edit_callback_message(
            callback,
            "Choose the new communication style:" if lang == LANG_EN else "Выберите новый стиль общения:",
            reply_markup=_tone_keyboard(lang),
        )
    elif field == "sales_strategy":
        await _send_or_edit_callback_message(
            callback,
            (
                "Choose the new sales funnel:"
                if lang == LANG_EN
                else "Выберите новую воронку продаж:"
            ),
            reply_markup=_strategy_keyboard(lang),
        )
    elif field == "working_hours":
        await _send_or_edit_callback_message(
            callback,
            _script_field_prompt(field, lang),
        )
    else:
        await _send_or_edit_callback_message(
            callback,
            _script_field_prompt(field, lang),
        )
    await callback.answer()


@router.callback_query(lambda c: c.data == "script:create")
async def confirm_create_script(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        script = Script(
            name=data["name"],
            role_prompt=data["role_prompt"],
            target_audience=data.get("target_audience"),
            goal=data["goal"],
            success_criteria=data.get("success_criteria"),
            tone=data.get("tone", "friendly"),
            sales_funnel=data.get("sales_funnel") or build_sales_funnel(
                data.get("sales_strategy")
            ),
            first_message_goal=data.get("first_message_goal", "trust"),
            call_to_action=data.get(
                "call_to_action",
                "short 10-minute call" if lang == LANG_EN else "короткий 10-минутный созвон",
            ),
            language=data.get("language", "ru"),
            emoji_policy=data.get("emoji_policy", "forbidden"),
            max_first_message_length=data.get("max_first_message_length", 240),
            max_messages=data.get("max_messages", 3),
            follow_up_delay_hours=data.get("follow_up_delay_hours", 24),
            working_hours_start=data.get("working_hours_start", dt_time(9, 0)),
            working_hours_end=data.get("working_hours_end", dt_time(18, 0)),
            timezone=data.get("timezone", "Europe/Moscow"),
            is_active=True,
        )
        session.add(script)
        await session.commit()
        await session.refresh(script)
    await state.clear()
    await callback.answer("✅ Business saved!" if lang == LANG_EN else "✅ Бизнес сохранен!")
    await callback.message.answer(
        (
            f"Business <b>{_html(script.name)}</b> is saved. Now upload contacts with /upload."
            if lang == LANG_EN
            else f"Бизнес <b>{_html(script.name)}</b> сохранен. Теперь можно загрузить контакты через /upload."
        ),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "script:cancel")
async def cancel_create_script(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    await state.clear()
    await callback.answer("❌ Cancelled" if lang == LANG_EN else "❌ Создание отменено")
    await callback.message.answer(
        "Business creation cancelled." if lang == LANG_EN else "Создание бизнеса отменено."
    )


# ---------------------------------------------------------------------------
# FSM: Import CSV / Excel
# ---------------------------------------------------------------------------


@router.message(Command("upload"))
async def cmd_upload(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    await state.set_state(CSVImportFSM.waiting_file)
    if lang == LANG_EN:
        text = (
            "Upload contacts, then choose a business and review the first message before launch.\n\n"
            "Send a CSV or Excel file.\n\n"
            "Required column: telegram_user_id or telegram_id.\n\n"
            "If this was accidental, choose another menu item or use /cancel.\n\n"
            "CSV example:\n"
            "first_name,last_name,company_name,position,city,industry,telegram_user_id,phone\n"
            "John,Doe,Acme,Founder,New York,SaaS,123456789,+10000000000"
        )
    else:
        text = (
            "Загрузите контакты, потом выберем бизнес и покажем первое сообщение перед запуском.\n\n"
            "Отправьте CSV или Excel-файл.\n\n"
            "Обязательная колонка: telegram_user_id (или telegram_id).\n\n"
            "Если открыли это случайно, выберите другой раздел в меню или напишите /cancel.\n\n"
            "Пример CSV:\n"
            "first_name,last_name,company_name,position,city,industry,telegram_user_id,phone\n"
            "Иван,Иванов,ООО Ромашка,Директор,Москва,IT,123456789,+79990000000"
        )
    await message.answer(
        text,
        reply_markup=_main_menu_keyboard(lang),
    )


@router.message(CSVImportFSM.waiting_file)
async def process_upload_file(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    if not message.document:
        await message.answer(
            "❌ Please send a file. To exit, choose another menu item or use /cancel."
            if lang == LANG_EN
            else "❌ Пожалуйста, отправьте файл. Чтобы выйти, выберите другой раздел в меню "
            "или напишите /cancel.",
            reply_markup=_main_menu_keyboard(lang),
        )
        return

    file_name = message.document.file_name.lower()
    if not (file_name.endswith(".csv") or file_name.endswith((".xlsx", ".xls"))):
        await message.answer(
            "❌ Only CSV and Excel files are accepted."
            if lang == LANG_EN
            else "❌ Принимаются только CSV и Excel файлы."
        )
        return

    bot = _get_bot()
    file = await bot.get_file(message.document.file_id)
    file_bytes = await bot.download_file(file.file_path)

    from app.services.contact_import import parse_csv, parse_excel

    try:
        contents = file_bytes.read()
        if file_name.endswith(".csv"):
            records = parse_csv(contents)
        else:
            records = parse_excel(contents)
    except ValueError as exc:
        error_text = str(exc)
        if error_text.startswith("Не найдена колонка"):
            await message.answer(
                "❌ Required column was not found. Check the file and try again."
                if lang == LANG_EN
                else f"❌ {error_text}. Проверьте файл и попробуйте снова."
            )
        else:
            await message.answer(
                f"❌ Parse error: {exc}" if lang == LANG_EN else f"❌ Ошибка парсинга: {exc}"
            )
        await state.clear()
        return

    preview = records[:3]
    preview_lines = []
    for idx, r in enumerate(preview, 1):
        preview_lines.append(
            f"{idx}. {r.get('first_name') or ''} {r.get('last_name') or ''} — "
            f"{r.get('company_name') or ''}, {r.get('position') or ''} "
            f"(@{r.get('telegram_username') or '-'}, {r.get('phone') or '-'})"
        )
    preview_text = "\n".join(preview_lines) if preview_lines else "(пустой файл)"

    await state.update_data(records=records)
    await state.set_state(CSVImportFSM.preview)

    if lang == LANG_EN:
        text = (
            f"📊 Found {len(records)} contacts.\n\n"
            f"First {len(preview)}:\n{preview_text}\n\n"
            "Next?"
        )
        choose_text = "✅ Choose business"
        cancel_text = "❌ Cancel"
    else:
        text = (
            f"📊 Найдено {len(records)} контактов.\n\n"
            f"Первые {len(preview)}:\n{preview_text}\n\n"
            f"Что делаем?"
        )
        choose_text = "✅ Выбрать бизнес"
        cancel_text = "❌ Отмена"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=choose_text, callback_data="csv:create_campaign"
                ),
                types.InlineKeyboardButton(
                    text=cancel_text, callback_data="csv:cancel"
                ),
            ]
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data == "csv:cancel")
async def cancel_csv_import(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    await state.clear()
    await callback.answer("❌ Import cancelled" if lang == LANG_EN else "❌ Импорт отменен")
    await callback.message.answer("Import cancelled." if lang == LANG_EN else "Импорт отменен.")


@router.callback_query(lambda c: c.data == "csv:create_campaign")
async def start_campaign_from_csv(callback: types.CallbackQuery, state: FSMContext):
    await _show_campaign_script_picker(callback, state)


def _is_message_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _send_or_edit_callback_message(
    callback: types.CallbackQuery,
    text: str,
    reply_markup: types.InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> str:
    """Prefer editing the bot message that owns an inline keyboard."""
    if callback.message is not None:
        try:
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return "edited"
        except TelegramBadRequest as exc:
            if _is_message_not_modified(exc):
                return "unchanged"
            logger.debug("Could not edit callback message, sending a new one: %s", exc)
            await callback.message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return "sent"

    return "missing_message"


async def _show_campaign_script_picker(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    lang = _admin_lang(callback)
    data = await state.get_data()
    records = data.get("records", [])
    if not records:
        await callback.answer("❌ No contacts" if lang == LANG_EN else "❌ Нет контактов")
        await state.clear()
        return

    await state.set_state(CampaignCreateFSM.select_script)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Script)
            .where(Script.is_active.is_(True))
            .order_by(Script.created_at.desc())
            .limit(20)
        )
        scripts = result.scalars().all()

    if not scripts:
        await _send_or_edit_callback_message(
            callback,
            (
                "❌ No active businesses. Describe a business first with /newscript."
                if lang == LANG_EN
                else "❌ Нет активных бизнесов. Сначала опишите бизнес через /newscript"
            ),
        )
        await state.clear()
        await callback.answer()
        return

    kb_rows = [
        [
            types.InlineKeyboardButton(
                text=s.name, callback_data=f"campaign_script:{s.id}"
            )
        ]
        for s in scripts
    ]
    kb_rows.append(
        [
            types.InlineKeyboardButton(
                text="❌ Cancel" if lang == LANG_EN else "❌ Отмена",
                callback_data="campaign_select:cancel",
            )
        ]
    )
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await _send_or_edit_callback_message(
        callback,
        (
            "Choose the business or offer for these contacts.\n\n"
            "After that I will show the first message before launch."
            if lang == LANG_EN
            else "Выберите бизнес или оффер для этих контактов.\n\n"
            "После выбора я покажу первое сообщение перед запуском."
        ),
        reply_markup=kb,
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# FSM: Campaign creation from import / discover
# ---------------------------------------------------------------------------


def _preview_keyboard(
    lang: str = LANG_RU,
    records_count: int = 1,
    *,
    showing_all: bool = False,
) -> types.InlineKeyboardMarkup:
    if lang == LANG_EN:
        launch_text = "✅ Launch"
        regenerate_text = "🔄 Regenerate"
        change_text = "✏️ Choose another business"
        show_all_text = f"👁 Show all {records_count}"
        show_first_text = "👁 Show first only"
    else:
        launch_text = "✅ Запустить"
        regenerate_text = "🔄 Перегенерировать"
        change_text = "✏️ Выбрать другой бизнес"
        show_all_text = f"👁 Показать все {records_count}"
        show_first_text = "👁 Только первое"

    rows = [
        [
            types.InlineKeyboardButton(
                text=launch_text, callback_data="preview:launch"
            ),
            types.InlineKeyboardButton(
                text=regenerate_text, callback_data="preview:regenerate"
            ),
        ],
    ]
    if records_count > 1:
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=show_first_text if showing_all else show_all_text,
                    callback_data="preview:show_first"
                    if showing_all
                    else "preview:show_all",
                )
            ],
        )
    rows.append(
        [
            types.InlineKeyboardButton(
                text=change_text, callback_data="preview:change_script"
            )
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _format_preview_text(
    preview_text: str,
    records_count: int,
    lang: str = LANG_RU,
) -> str:
    if records_count <= 1:
        return (
            f"First-message preview:\n\n{preview_text}"
            if lang == LANG_EN
            else f"Предпросмотр первого сообщения:\n\n{preview_text}"
        )
    if lang == LANG_EN:
        return (
            f"First-message preview (1 of {records_count}):\n\n"
            f"{preview_text}\n\n"
            f"Only the first contact is shown. You can show all {records_count} generated messages before launch."
        )
    return (
        f"Предпросмотр первого сообщения (1 из {records_count}):\n\n"
        f"{preview_text}\n\n"
        f"Показан первый контакт. Перед запуском можно вывести все {records_count} сгенерированных сообщений."
    )


def _preview_record_label(record: dict, idx: int, lang: str = LANG_RU) -> str:
    name = " ".join(
        str(record.get(field) or "").strip()
        for field in ("first_name", "last_name")
        if str(record.get(field) or "").strip()
    )
    company = str(record.get("company_name") or "").strip()
    position = str(record.get("position") or "").strip()
    parts = [part for part in (name, position, company) if part]
    if not parts:
        return f"Contact {idx}" if lang == LANG_EN else f"Контакт {idx}"
    return " · ".join(parts)


def _format_all_preview_text(
    previews: list[tuple[dict, str]],
    lang: str = LANG_RU,
) -> str:
    title = (
        f"Generated first messages ({len(previews)}):"
        if lang == LANG_EN
        else f"Сгенерированные первые сообщения ({len(previews)}):"
    )
    blocks = [title]
    for idx, (record, preview_text) in enumerate(previews, 1):
        label = _preview_record_label(record, idx, lang)
        blocks.append(f"{idx}. {_html(label)}\n{_html(preview_text)}")
    return "\n\n".join(blocks)


async def _generate_preview_message(script: Script, record: dict) -> str:
    stage = get_first_stage(script)
    contact = SimpleNamespace(**record)
    messages = [
        {
            "role": "system",
            "content": build_system_prompt(script, conversation_stage=stage),
        },
        {
            "role": "user",
            "content": build_initial_user_prompt(
                script, contact, conversation_stage=stage
            ),
        },
    ]
    try:
        engine = LLMEngine()
        result = await engine.generate_response_with_guardrails(
            messages,
            last_messages=[],
            max_retries=2,
            max_tokens=get_max_length_for_stage(script, stage),
        )
        text = (result.get("text") or "").strip()
        if not text or result.get("model") == "fallback":
            return build_safe_initial_fallback(contact, script)
        if needs_initial_message_retry(text):
            retry_result = await engine.generate_response_with_guardrails(
                [
                    *messages,
                    {
                        "role": "user",
                        "content": build_initial_message_retry_prompt(text),
                    },
                ],
                last_messages=[],
                max_retries=1,
                max_tokens=get_max_length_for_stage(script, stage),
            )
            retry_text = retry_result.get("text", "")
            if (
                retry_text
                and retry_result.get("model") != "fallback"
                and not needs_initial_message_retry(retry_text)
            ):
                return retry_text
            return build_safe_initial_fallback(contact, script)
        return text
    except Exception:
        logger.exception("Failed to generate campaign preview")
        return build_safe_initial_fallback(contact, script)


@router.callback_query(lambda c: c.data and c.data.startswith("campaign_script:"))
async def process_campaign_script(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    script_id_str = callback.data.split(":", 1)[1]
    try:
        script_id = UUID(script_id_str)
    except ValueError:
        await callback.answer("❌ Invalid business ID" if lang == LANG_EN else "❌ Неверный ID бизнеса")
        await state.clear()
        return

    data = await state.get_data()
    records = data.get("records", [])
    if not records:
        await callback.answer("❌ No contacts" if lang == LANG_EN else "❌ Нет контактов")
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()

    if not script:
        await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
        await state.clear()
        return

    await state.update_data(script_id=script_id)
    preview_text = await _generate_preview_message(script, records[0])
    await state.update_data(preview_text=preview_text)
    await state.set_state(CampaignCreateFSM.preview)

    text = _format_preview_text(preview_text, len(records), lang)
    await _send_or_edit_callback_message(
        callback, text, reply_markup=_preview_keyboard(lang, len(records))
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "preview:regenerate")
async def handle_preview_regenerate(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    data = await state.get_data()
    script_id = data.get("script_id")
    records = data.get("records", [])
    if not script_id or not records:
        await callback.answer("❌ Session expired" if lang == LANG_EN else "❌ Сессия устарела")
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()

    if not script:
        await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
        await state.clear()
        return

    preview_text = await _generate_preview_message(script, records[0])
    await state.update_data(preview_text=preview_text)
    text = _format_preview_text(preview_text, len(records), lang)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=_preview_keyboard(lang, len(records)),
        )
    except TelegramBadRequest as exc:
        if not _is_message_not_modified(exc):
            raise
        await callback.answer("No changes" if lang == LANG_EN else "Без изменений")
        return
    await callback.answer("🔄 Updated" if lang == LANG_EN else "🔄 Обновлено")


@router.callback_query(lambda c: c.data == "preview:show_all")
async def handle_preview_show_all(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    data = await state.get_data()
    script_id = data.get("script_id")
    records = data.get("records", [])
    if not script_id or not records:
        await callback.answer("❌ Session expired" if lang == LANG_EN else "❌ Сессия устарела")
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()

    if not script:
        await callback.answer("❌ Business not found" if lang == LANG_EN else "❌ Бизнес не найден")
        await state.clear()
        return

    await callback.answer("Generating..." if lang == LANG_EN else "Генерирую...")
    previews: list[tuple[dict, str]] = []
    for record in records:
        previews.append((record, await _generate_preview_message(script, record)))

    await state.update_data(preview_messages=[text for _, text in previews])
    chunks = _split_long_text(_format_all_preview_text(previews, lang))
    keyboard = _preview_keyboard(lang, len(records), showing_all=True)
    if len(chunks) == 1:
        try:
            await callback.message.edit_text(
                chunks[0],
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except TelegramBadRequest as exc:
            if not _is_message_not_modified(exc):
                raise
    else:
        for chunk in chunks[:-1]:
            await callback.message.answer(chunk, parse_mode="HTML")
        await callback.message.answer(chunks[-1], reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "preview:show_first")
async def handle_preview_show_first(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    data = await state.get_data()
    records = data.get("records", [])
    preview_text = data.get("preview_text")
    if not preview_text or not records:
        await callback.answer("❌ Session expired" if lang == LANG_EN else "❌ Сессия устарела")
        await state.clear()
        return

    text = _format_preview_text(preview_text, len(records), lang)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=_preview_keyboard(lang, len(records)),
        )
    except TelegramBadRequest as exc:
        if not _is_message_not_modified(exc):
            raise
        await callback.answer("No changes" if lang == LANG_EN else "Без изменений")
        return
    await callback.answer()


@router.callback_query(lambda c: c.data == "preview:change_script")
async def handle_preview_change_script(
    callback: types.CallbackQuery, state: FSMContext
):
    await _show_campaign_script_picker(callback, state)


@router.callback_query(lambda c: c.data == "campaign_select:cancel")
async def cancel_campaign_script_selection(
    callback: types.CallbackQuery, state: FSMContext
):
    lang = _admin_lang(callback)
    await state.clear()
    await callback.answer("❌ Cancelled" if lang == LANG_EN else "❌ Отменено")
    await _send_or_edit_callback_message(
        callback,
        "Launch creation cancelled." if lang == LANG_EN else "Создание запуска отменено.",
    )


@router.callback_query(lambda c: c.data == "preview:launch")
async def handle_preview_launch(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    await state.set_state(CampaignCreateFSM.name)
    await callback.message.answer(
        (
            "What should we call this launch?\n\n"
            "Example: Moscow coffee shops, July. This name is only for your admin panel."
            if lang == LANG_EN
            else "Как назвать этот запуск?\n\n"
            "Например: «Кофейни Москва, июль». Это название только для вашей админки."
        )
    )
    await callback.answer()


@router.message(CampaignCreateFSM.name)
async def process_campaign_name(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    await state.update_data(campaign_name=message.text)
    data = await state.get_data()
    await state.set_state(CampaignCreateFSM.confirm)

    script_id = data.get("script_id")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()

    if lang == LANG_EN:
        text = (
            f"Launch review:\n\n"
            f"Launch: {data['campaign_name']}\n"
            f"Business: {script.name if script else '—'}\n"
            f"Contacts: {len(data.get('records', []))}\n\n"
            f"First message:\n{data.get('preview_text', '—')}\n\n"
            f"Start now?"
        )
        start_text = "▶️ Start"
        later_text = "⏸ Save draft"
        cancel_text = "❌ Cancel"
    else:
        text = (
            f"Сводка перед запуском:\n\n"
            f"Запуск: {data['campaign_name']}\n"
            f"Бизнес: {script.name if script else '—'}\n"
            f"Контактов: {len(data.get('records', []))}\n\n"
            f"Первое сообщение:\n{data.get('preview_text', '—')}\n\n"
            f"Запустить?"
        )
        start_text = "▶️ Запустить"
        later_text = "⏸ Сохранить черновик"
        cancel_text = "❌ Отмена"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=start_text, callback_data="campaign:start_now"
                ),
                types.InlineKeyboardButton(
                    text=later_text, callback_data="campaign:start_later"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=cancel_text, callback_data="campaign:cancel"
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data == "campaign:cancel")
async def cancel_campaign_create(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    await state.clear()
    await callback.answer("❌ Cancelled" if lang == LANG_EN else "❌ Создание отменено")
    await callback.message.answer(
        "Launch creation cancelled." if lang == LANG_EN else "Создание запуска отменено."
    )


@router.callback_query(lambda c: c.data == "campaign:start_later")
async def campaign_start_later(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    data = await state.get_data()
    records = data.get("records", [])

    async with AsyncSessionLocal() as session:
        script_id = data.get("script_id")
        campaign = Campaign(
            script_id=script_id,
            name=data["campaign_name"],
            status="draft",
            total_contacts=len(records),
        )
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)

        from app.services.contact_import import contacts_in_record_order, upsert_contacts

        created, updated = await upsert_contacts(session, records, source="csv_import")
        contacts = contacts_in_record_order(records, created + updated)

        for queue_position, contact in enumerate(contacts, start=1):
            cc = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="pending",
                message_count=0,
                queue_position=queue_position,
            )
            session.add(cc)

        campaign.total_contacts = len(contacts)
        await session.commit()

    await state.clear()
    await callback.answer("✅ Draft saved" if lang == LANG_EN else "✅ Черновик сохранен")
    await callback.message.answer(
        (
            f"Launch <b>{_html(campaign.name)}</b> was saved as a draft. Start it with /startcampaign."
            if lang == LANG_EN
            else f"Запуск <b>{_html(campaign.name)}</b> сохранен как черновик. Запустите через /startcampaign."
        ),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "campaign:start_now")
async def campaign_start_now(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    data = await state.get_data()
    records = data.get("records", [])

    async with AsyncSessionLocal() as session:
        script_id = data.get("script_id")
        script = None
        if script_id:
            script_result = await session.execute(
                select(Script).where(Script.id == script_id)
            )
            script_candidate = script_result.scalar_one_or_none()
            script = script_candidate if isinstance(script_candidate, Script) else None
        campaign = Campaign(
            script_id=script_id,
            name=data["campaign_name"],
            status="running",
            total_contacts=len(records),
            started_at=datetime.now(timezone.utc),
        )
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)

        from app.services.contact_import import contacts_in_record_order, upsert_contacts

        created, updated = await upsert_contacts(session, records, source="csv_import")
        contacts = contacts_in_record_order(records, created + updated)

        for queue_position, contact in enumerate(contacts, start=1):
            cc = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="pending",
                message_count=0,
                queue_position=queue_position,
            )
            session.add(cc)

        campaign.total_contacts = len(contacts)
        await session.commit()

    await state.clear()
    await callback.answer("✅ Launch started!" if lang == LANG_EN else "✅ Запуск начат!")
    notice = _launch_queue_notice(campaign.total_contacts or 0, lang)
    notice += _launch_timing_notice(script, lang)
    await callback.message.answer(
        (
            f"Launch <b>{_html(campaign.name)}</b> started with {campaign.total_contacts} contacts."
            if lang == LANG_EN
            else f"Запуск <b>{_html(campaign.name)}</b> начат с {campaign.total_contacts} контактами."
        )
        + notice,
        parse_mode="HTML",
    )

    # Process campaign in background so the bot UI stays responsive.
    from app.core.scheduler import process_campaigns

    _schedule_process_campaign(campaign.id, process_campaigns)


def _schedule_process_campaign(campaign_id, process_campaigns_fn):
    """Schedule campaign processing without blocking the bot response."""
    return asyncio.create_task(
        _process_campaign_safely(campaign_id, process_campaigns_fn)
    )


async def _process_campaign_safely(campaign_id, process_campaigns_fn):
    """Run process_campaigns in a fresh session and log any errors."""
    try:
        async with AsyncSessionLocal() as session:
            await process_campaigns_fn(session)
    except Exception:
        logger.exception(
            "Background process_campaigns failed for campaign %s", campaign_id
        )


# ---------------------------------------------------------------------------
# FSM: Discover Leads (reuse campaign creation)
# ---------------------------------------------------------------------------


@router.message(Command("discover"))
async def cmd_discover(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    await state.set_state(DiscoverFSM.business_description)
    if lang == LANG_EN:
        text = (
            "Lead search through Telegram public messages.\n\n"
            "I will build search queries from your business and ICP, search public Telegram messages "
            "through the connected seller account, collect visible authors, and return a CSV for Upload.\n\n"
            "Step 1: describe your business or offer. What do you sell and why is it useful?"
        )
    else:
        text = (
            "Поиск лидов через публичные сообщения Telegram.\n\n"
            "Я соберу поисковые запросы из описания бизнеса и ЦА, найду публичные сообщения "
            "через подключенный аккаунт продавца, соберу видимых авторов и верну CSV для Upload.\n\n"
            "Шаг 1: опишите ваш бизнес или оффер. Что продаете и почему это полезно?"
        )
    await message.answer(text, reply_markup=_main_menu_keyboard(lang))


class DiscoverFSM(StatesGroup):
    business_description = State()
    audience_description = State()
    country = State()
    language = State()
    pain_keywords = State()
    limit = State()
    confirm = State()


DISCOVERY_CSV_COLUMNS = [
    "first_name",
    "last_name",
    "company_name",
    "position",
    "city",
    "industry",
    "telegram_user_id",
    "telegram_username",
    "phone",
    "source",
    "last_source",
    "source_url",
    "source_summary",
    "source_message_text",
    "source_message_date",
    "is_valid",
    "icp_score",
]


def _discovery_csv_bytes(records: list[dict[str, Any]]) -> bytes:
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=DISCOVERY_CSV_COLUMNS,
        extrasaction="ignore",
    )
    writer.writeheader()
    for record in records:
        writer.writerow(
            {column: record.get(column, "") for column in DISCOVERY_CSV_COLUMNS}
        )
    return output.getvalue().encode("utf-8-sig")


async def _send_discovery_csv(
    message: types.Message,
    records: list[dict[str, Any]],
    lang: str = LANG_RU,
) -> None:
    csv_bytes = _discovery_csv_bytes(records)
    caption = (
        f"Telegram lead search result: {len(records)} contacts. This CSV can be uploaded with Contacts & launch."
        if lang == LANG_EN
        else f"Результат поиска Telegram: {len(records)} контактов. Этот CSV можно загрузить через «Контакты и запуск»."
    )
    bot = _get_bot()
    await bot.send_document(
        chat_id=message.chat.id,
        document=types.BufferedInputFile(csv_bytes, filename="telegram_leads.csv"),
        caption=caption,
    )


def _telegram_search_missing_text(lang: str = LANG_RU) -> str:
    if lang == LANG_EN:
        return (
            "Telegram lead search needs a connected seller account.\n\n"
            "Add TELEGRAM_API_ID, TELEGRAM_API_HASH, and at least one ready/active seller account "
            "with a session string. No paid directory API token is required."
        )
    return (
        "Для поиска лидов нужен подключенный аккаунт продавца.\n\n"
        "Нужны TELEGRAM_API_ID, TELEGRAM_API_HASH и хотя бы один ready/active аккаунт "
        "с session string. Токен внешнего платного каталога больше не нужен."
    )


async def _start_discovery_seller_client(
    source: str,
) -> tuple[Any | None, Any | None, str | None]:
    if source not in {"telegram_search", "channel_parse"}:
        return None, None, None

    settings = get_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        return None, None, "telegram_api_missing"

    from app.bots.seller_client import SellerClient
    from app.models.telegram_account import TelegramAccount

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TelegramAccount)
            .where(TelegramAccount.status.in_(["ready", "active"]))
            .where(TelegramAccount.session_string.isnot(None))
            .order_by(TelegramAccount.last_message_at.asc().nullsfirst())
            .limit(1)
        )
        account = result.scalar_one_or_none()

    if not account or not account.session_string:
        return None, None, "telegram_account_missing"

    seller_client = SellerClient(
        account_id=str(account.id),
        session_string=account.session_string,
        proxy_url=account.proxy_url,
        api_id=settings.telegram_api_id or None,
        api_hash=settings.telegram_api_hash or None,
        no_updates=True,
    )
    try:
        await seller_client.start()
    except Exception:
        logger.exception("Failed to start seller client for lead discovery")
        await seller_client.stop()
        return None, None, "telegram_client_failed"

    if seller_client._client is None:
        await seller_client.stop()
        return None, None, "telegram_client_failed"
    return seller_client._client, seller_client, None


def _discovery_config_error_text(error_code: str | None, source: str, lang: str = LANG_RU) -> str:
    if source == "external_api":
        if lang == LANG_EN:
            return (
                "External lead search is not connected yet.\n\n"
                "Add EXTERNAL_LEAD_API_URL to .env. The endpoint should accept "
                "q and limit and return contacts as JSON. "
                "Until then, use CSV upload or Telegram search with a connected seller account."
            )
        return (
            "Внешний поиск лидов пока не подключен.\n\n"
            "Добавьте EXTERNAL_LEAD_API_URL в .env. Endpoint должен принимать "
            "q и limit и возвращать контакты JSON. "
            "Пока можно использовать CSV или Telegram-поиск через подключенный аккаунт продавца."
        )
    if error_code == "telegram_api_missing":
        if lang == LANG_EN:
            return "Telegram search needs TELEGRAM_API_ID and TELEGRAM_API_HASH in .env."
        return "Для Telegram-поиска нужны TELEGRAM_API_ID и TELEGRAM_API_HASH в .env."
    if error_code == "telegram_account_missing":
        if lang == LANG_EN:
            return (
                "Telegram search needs at least one seller account with status ready/active and a session string. "
                "Add the account in the admin/API first."
            )
        return (
            "Для Telegram-поиска нужен хотя бы один аккаунт продавца со статусом ready/active и session string. "
            "Сначала добавьте аккаунт в админке/API."
        )
    if lang == LANG_EN:
        return "Telegram discovery client could not start. Check account session, proxy, and logs."
    return "Клиент Telegram для поиска не запустился. Проверьте session, proxy и логи."


@router.message(DiscoverFSM.business_description)
async def process_discover_business(message: types.Message, state: FSMContext):
    await state.update_data(business_description=message.text)
    await state.set_state(DiscoverFSM.audience_description)
    lang = _admin_lang(message)
    await message.answer(
        (
            "Step 2: describe the target audience.\n\n"
            "Include roles, industry, company size, and who can make or influence the buying decision."
        )
        if lang == LANG_EN
        else (
            "Шаг 2: опишите целевую аудиторию.\n\n"
            "Укажите роли, отрасль, размер компаний и кто может принимать или влиять на решение."
        )
    )


@router.message(DiscoverFSM.audience_description)
async def process_discover_audience(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    await state.update_data(audience_description=message.text)
    await state.set_state(DiscoverFSM.country)
    await message.answer(
        (
            "Step 3: country or market.\n\n"
            "Example: Poland, Germany, United States, Russia."
        )
        if lang == LANG_EN
        else (
            "Шаг 3: страна или рынок.\n\n"
            "Например: Польша, Германия, США, Россия."
        )
    )


@router.message(DiscoverFSM.country)
async def process_discover_country(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    await state.update_data(country=message.text)
    await state.set_state(DiscoverFSM.language)
    await message.answer(
        (
            "Step 4: language for local Telegram search.\n\n"
            "Example: Polish, English, German, Russian."
        )
        if lang == LANG_EN
        else (
            "Шаг 4: язык локального поиска в Telegram.\n\n"
            "Например: польский, английский, немецкий, русский."
        )
    )


@router.message(DiscoverFSM.language)
async def process_discover_language(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    await state.update_data(language=message.text)
    await state.set_state(DiscoverFSM.pain_keywords)
    await message.answer(
        (
            "Step 5: what need signals should we look for?\n\n"
            "Examples: looking for CRM, recommend ERP, warehouse automation, need IT contractor. "
            "Send '-' if you want me to use generic B2B need signals."
        )
        if lang == LANG_EN
        else (
            "Шаг 5: какие признаки потребности искать?\n\n"
            "Примеры: ищем CRM, посоветуйте ERP, автоматизация склада, нужен IT-подрядчик. "
            "Отправьте '-', если использовать общие B2B-сигналы."
        )
    )


@router.message(DiscoverFSM.pain_keywords)
async def process_discover_pains(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    text = (message.text or "").strip()
    await state.update_data(pain_keywords="" if text == "-" else text)
    await state.set_state(DiscoverFSM.limit)
    await message.answer(
        (
            "Step 6: how many contacts should I return in the CSV?\n\n"
            "Usually 20-50 for the first run."
        )
        if lang == LANG_EN
        else (
            "Шаг 6: сколько контактов вернуть в CSV?\n\n"
            "Для первого запуска обычно 20-50."
        )
    )


@router.callback_query(lambda c: c.data and c.data.startswith("discover_action:"))
async def process_discover_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 1)[1]
    lang = _admin_lang(callback)
    if action == "cancel":
        await state.clear()
        await callback.answer("Cancelled" if lang == LANG_EN else "Отменено")
        if callback.message:
            await _send_or_edit_callback_message(
                callback,
                "Lead search cancelled." if lang == LANG_EN else "Поиск лидов отменен.",
            )
        return
    if action == "upload" and callback.message:
        await state.clear()
        await callback.answer()
        await cmd_upload(callback.message, state)
        return
    await callback.answer()


@router.message(DiscoverFSM.limit)
async def process_discover_limit(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    text = message.text.strip()
    try:
        limit = int(text) if text else 20
    except ValueError:
        limit = 20

    await state.update_data(limit=limit)
    data = await state.get_data()
    from app.services.telegram_global_lead_search import (
        TelegramGlobalLeadSearch,
        TelegramGlobalSearchCriteria,
    )

    telegram_client, seller_client, error_code = await _start_discovery_seller_client("telegram_search")
    if error_code:
        await message.answer(_discovery_config_error_text(error_code, "telegram_search", lang))
        await state.clear()
        return

    criteria = TelegramGlobalSearchCriteria(
        business_description=data.get("business_description", ""),
        audience_description=data.get("audience_description", ""),
        country=data.get("country", ""),
        language=data.get("language", ""),
        pain_keywords=data.get("pain_keywords", ""),
        limit=limit,
    )

    await message.answer(
        (
            "⏳ Searching public Telegram messages via MTProto and collecting visible authors. "
            "This can take a minute."
            if lang == LANG_EN
            else "⏳ Ищу публичные сообщения Telegram через MTProto и собираю видимых авторов. "
            "Это может занять около минуты."
        )
    )

    try:
        searcher = TelegramGlobalLeadSearch()
        search_result = await searcher.run(criteria, telegram_client=telegram_client)
    except Exception as exc:
        logger.exception("Discover failed")
        await message.answer(
            f"❌ Search failed: {exc}" if lang == LANG_EN else f"❌ Ошибка при поиске: {exc}"
        )
        await state.clear()
        return
    finally:
        if seller_client is not None:
            await seller_client.stop()

    results = search_result.records
    await _send_discovery_csv(message, results, lang)

    await state.update_data(
        discovered=results,
        records=results,
        source="telegram_search",
        discovery_queries=search_result.queries,
        discovery_groups=search_result.groups,
        discovery_errors=search_result.errors,
    )
    await state.set_state(DiscoverFSM.confirm)

    preview_lines = []
    for idx, r in enumerate(results[:5], 1):
        username = r.get("telegram_username") or "-"
        summary = _compact(r.get("source_summary"), 120)
        preview_lines.append(
            f"{idx}. @{username} — {r.get('first_name') or ''} {r.get('last_name') or ''}\n{summary}"
        )
    preview_text = (
        "\n".join(preview_lines)
        if preview_lines
        else ("(no preview data)" if lang == LANG_EN else "(нет данных для предпросмотра)")
    )

    if lang == LANG_EN:
        text = (
            f"Done. CSV sent.\n\n"
            f"Contacts: {len(results)}\n"
            f"Search queries: {', '.join(search_result.queries[:8])}\n"
            f"Public chats found: {len(search_result.groups)}\n"
            f"Messages checked: {search_result.posts_checked}\n\n"
            f"First {min(len(results), 5)}:\n{preview_text}\n\n"
            f"You can upload the CSV manually or save these contacts now."
        )
        add_text = "✅ Add and create launch"
        csv_text = "📄 Send CSV again"
        preview_button_text = "📋 Preview"
        cancel_text = "❌ Cancel"
    else:
        text = (
            f"Готово. CSV отправлен.\n\n"
            f"Контактов: {len(results)}\n"
            f"Поисковые запросы: {', '.join(search_result.queries[:8])}\n"
            f"Найдено публичных чатов: {len(search_result.groups)}\n"
            f"Проверено сообщений: {search_result.posts_checked}\n\n"
            f"Первые {min(len(results), 5)}:\n{preview_text}\n\n"
            f"Можно загрузить CSV вручную или сразу сохранить контакты."
        )
        add_text = "✅ Добавить и создать запуск"
        csv_text = "📄 Отправить CSV еще раз"
        preview_button_text = "📋 Предпросмотр"
        cancel_text = "❌ Отмена"
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=add_text,
                    callback_data="discover_confirm:add",
                ),
                types.InlineKeyboardButton(
                    text=preview_button_text,
                    callback_data="discover_confirm:preview",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text=csv_text,
                    callback_data="discover_confirm:csv",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text=cancel_text,
                    callback_data="discover_confirm:cancel",
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("discover_confirm:"))
async def process_discover_confirm(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    action = callback.data.split(":", 1)[1]
    data = await state.get_data()
    discovered = data.get("discovered", [])

    if action == "cancel":
        await state.clear()
        await callback.answer("❌ Cancelled" if lang == LANG_EN else "❌ Отменено")
        await callback.message.answer("Search cancelled." if lang == LANG_EN else "Поиск отменен.")
        return

    if action == "preview":
        lines = []
        for idx, r in enumerate(discovered, 1):
            name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
            summary = _compact(r.get("source_summary"), 220)
            source_url = r.get("source_url") or "—"
            lines.append(
                f"{idx}. @{r.get('telegram_username') or '-'} — {name or '—'}\n"
                f"{summary}\n"
                f"{source_url}"
            )
        text = "\n".join(lines) if lines else ("(empty)" if lang == LANG_EN else "(пусто)")
        await callback.answer()
        await callback.message.answer(
            f"📋 Full list:\n\n{text}" if lang == LANG_EN else f"📋 Полный список:\n\n{text}"
        )
        return

    if action == "csv":
        await _send_discovery_csv(callback.message, discovered, lang)
        await callback.answer("CSV sent" if lang == LANG_EN else "CSV отправлен")
        return

    if action == "add":
        async with AsyncSessionLocal() as session:
            from app.services.contact_import import upsert_contacts

            try:
                created, updated = await upsert_contacts(
                    session, discovered, source=data.get("source", "discover")
                )
            except Exception as exc:
                logger.exception("Failed to save discovered contacts")
                await state.clear()
                await callback.answer("❌ Error" if lang == LANG_EN else "❌ Ошибка")
                await callback.message.answer(
                    f"Save error: {exc}" if lang == LANG_EN else f"Ошибка сохранения: {exc}"
                )
                return

        await callback.answer("✅ Added!" if lang == LANG_EN else "✅ Добавлено!")
        await callback.message.answer(
            (
                f"✅ Saved {len(created)} new and updated {len(updated)} contacts.\n"
                f"Now let's create a launch."
                if lang == LANG_EN
                else f"✅ Сохранено {len(created)} новых и обновлено {len(updated)} контактов.\n"
                f"Теперь создадим запуск."
            )
        )
        await start_campaign_from_csv(callback, state)
        return

    await callback.answer()


# ---------------------------------------------------------------------------
# FSM: Start Campaign
# ---------------------------------------------------------------------------


@router.message(Command("startcampaign"))
async def cmd_startcampaign(message: types.Message, state: FSMContext):
    lang = _admin_lang(message)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Campaign)
            .where(Campaign.status == "draft")
            .order_by(Campaign.created_at.desc())
            .limit(20)
        )
        campaigns = result.scalars().all()

    if not campaigns:
        await message.answer(
            (
                "No saved drafts.\n\n"
                "To start outreach, open Contacts & launch, upload a file, and choose a business."
                if lang == LANG_EN
                else "Черновиков запуска нет.\n\n"
                "Если хотите начать рассылку, откройте «Контакты и запуск», загрузите файл "
                "и выберите бизнес."
            )
        )
        return

    await state.set_state(CampaignStartFSM.selecting)
    kb_rows = []
    for c in campaigns:
        kb_rows.append(
            [types.InlineKeyboardButton(text=c.name, callback_data=f"startcamp:{c.id}")]
        )
    kb_rows.append(
        [
            types.InlineKeyboardButton(
                text="❌ Cancel" if lang == LANG_EN else "❌ Отмена",
                callback_data="startcamp:cancel",
            )
        ]
    )
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await message.answer(
        "Choose a saved launch draft:" if lang == LANG_EN else "Выберите сохраненный черновик запуска:",
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("startcamp:"))
async def handle_startcamp(callback: types.CallbackQuery, state: FSMContext):
    lang = _admin_lang(callback)
    camp_id_str = callback.data.split(":", 1)[1]
    if camp_id_str == "cancel":
        await state.clear()
        await callback.answer("Cancelled" if lang == LANG_EN else "Отменено")
        await callback.message.answer(
            "Launch cancelled." if lang == LANG_EN else "Запуск отменен."
        )
        return

    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Invalid ID" if lang == LANG_EN else "❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        script = None
        if not campaign:
            await callback.answer("❌ Launch not found" if lang == LANG_EN else "❌ Запуск не найден")
            await state.clear()
            return
        if campaign.status != "draft":
            await callback.answer(
                "❌ This launch is not a draft anymore"
                if lang == LANG_EN
                else "❌ Этот запуск уже не черновик"
            )
            await state.clear()
            return

        script_result = await session.execute(select(Script).where(Script.id == campaign.script_id))
        script_candidate = script_result.scalar_one_or_none()
        script = script_candidate if isinstance(script_candidate, Script) else None

        campaign.status = "running"
        campaign.started_at = datetime.now(timezone.utc)
        await session.commit()

        from app.core.scheduler import process_campaigns

        processing_failed = False
        try:
            await process_campaigns(session)
        except Exception:
            processing_failed = True
            logger.exception("Immediate process_campaigns failed after campaign start")

    await state.clear()
    if processing_failed:
        await callback.answer(
            "⚠️ Launch started, sending will retry"
            if lang == LANG_EN
            else "⚠️ Запуск начат, отправка будет повторена"
        )
        await callback.message.answer(
            (
                f"Launch <b>{_html(campaign.name)}</b> started, but the first sending attempt did not finish. "
                "The scheduler will retry automatically; the error was written to logs."
                if lang == LANG_EN
                else f"Запуск <b>{_html(campaign.name)}</b> начат, но первая попытка отправки "
                "не завершилась. Планировщик повторит обработку автоматически; ошибка "
                "записана в логи."
            ),
            parse_mode="HTML",
        )
    else:
        await callback.answer("✅ Launch started!" if lang == LANG_EN else "✅ Запуск начат!")
        notice = _launch_queue_notice(campaign.total_contacts or 0, lang)
        notice += _launch_timing_notice(script, lang)
        await callback.message.answer(
            (
                f"Launch <b>{_html(campaign.name)}</b> started."
                if lang == LANG_EN
                else f"Запуск <b>{_html(campaign.name)}</b> начат."
            )
            + notice,
            parse_mode="HTML",
        )


MENU_HANDLERS = {
    MENU_SCRIPTS: cmd_scripts,
    MENU_NEW_SCRIPT: cmd_newscript,
    MENU_CAMPAIGNS: cmd_campaigns,
    MENU_START_CAMPAIGN: cmd_startcampaign,
    MENU_UPLOAD: cmd_upload,
    MENU_DISCOVER: cmd_discover,
    MENU_ANALYTICS: cmd_analytics,
    MENU_HOT_LEADS: cmd_hotleads,
    MENU_CONVERSATIONS: cmd_conversations,
    MENU_HELP: cmd_help,
    MENU_SCRIPTS_EN: cmd_scripts,
    MENU_NEW_SCRIPT_EN: cmd_newscript,
    MENU_CAMPAIGNS_EN: cmd_campaigns,
    MENU_START_CAMPAIGN_EN: cmd_startcampaign,
    MENU_UPLOAD_EN: cmd_upload,
    MENU_DISCOVER_EN: cmd_discover,
    MENU_ANALYTICS_EN: cmd_analytics,
    MENU_HOT_LEADS_EN: cmd_hotleads,
    MENU_CONVERSATIONS_EN: cmd_conversations,
    MENU_HELP_EN: cmd_help,
    "🧩 Сценарии": cmd_scripts,
    "➕ Новый сценарий": cmd_newscript,
    "📣 Кампании": cmd_campaigns,
    "🚀 Запуск кампании": cmd_startcampaign,
    "📤 Импорт контактов": cmd_upload,
    "Scripts": cmd_scripts,
    "New Script": cmd_newscript,
    "Campaigns": cmd_campaigns,
    "Start Campaign": cmd_startcampaign,
    "Upload": cmd_upload,
    "Discover": cmd_discover,
    "Analytics": cmd_analytics,
    "Hot Leads": cmd_hotleads,
    "Conversations": cmd_conversations,
    "Help": cmd_help,
}
STATEFUL_MENU_BUTTONS = {
    MENU_NEW_SCRIPT,
    MENU_START_CAMPAIGN,
    MENU_UPLOAD,
    MENU_DISCOVER,
    MENU_NEW_SCRIPT_EN,
    MENU_START_CAMPAIGN_EN,
    MENU_UPLOAD_EN,
    MENU_DISCOVER_EN,
    "➕ Новый сценарий",
    "🚀 Запуск кампании",
    "📤 Импорт контактов",
    "New Script",
    "Start Campaign",
    "Upload",
    "Discover",
}
COMMAND_HANDLERS = {
    "/start": (cmd_start, False),
    "/help": (cmd_help, False),
    "/cancel": (cmd_cancel, True),
    "/back": (cmd_back, True),
    "/scripts": (cmd_scripts, False),
    "/campaigns": (cmd_campaigns, False),
    "/upload": (cmd_upload, True),
    "/analytics": (cmd_analytics, False),
    "/hotleads": (cmd_hotleads, False),
    "/newscript": (cmd_newscript, True),
    "/startcampaign": (cmd_startcampaign, True),
    "/discover": (cmd_discover, True),
    "/conversations": (cmd_conversations, False),
}


async def _dispatch_navigation_override(message: types.Message, state: FSMContext) -> bool:
    text = (message.text or "").strip()
    if not text:
        return False

    if text in MENU_HANDLERS:
        await state.clear()
        handler = MENU_HANDLERS[text]
        if text in STATEFUL_MENU_BUTTONS:
            await handler(message, state)
        else:
            await handler(message)
        return True

    if not text.startswith("/"):
        return False

    command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
    handler_info = COMMAND_HANDLERS.get(command)
    if not handler_info:
        await message.answer(
            (
                "Unknown command was not saved as an answer in the current wizard.\n\n"
                "Use the menu, /help, or /cancel."
                if _admin_lang(message) == LANG_EN
                else "Неизвестная команда не будет записана как ответ в текущем мастере.\n\n"
                "Используйте меню, /help или /cancel."
            ),
            reply_markup=_main_menu_keyboard(_admin_lang(message)),
        )
        return True

    handler, needs_state = handler_info
    if command not in {"/cancel", "/back"}:
        await state.clear()
    if needs_state:
        await handler(message, state)
    else:
        await handler(message)
    return True


def _state_name(state: State) -> str:
    return state.state


CALLBACK_STATE_REQUIREMENTS: list[tuple[Callable[[str], bool], str]] = [
    (lambda data: data.startswith("tone:"), _state_name(ScriptCreateFSM.tone)),
    (lambda data: data.startswith("strategy:"), _state_name(ScriptCreateFSM.sales_strategy)),
    (lambda data: data.startswith("fmg:"), _state_name(ScriptCreateFSM.first_message_goal)),
    (lambda data: data.startswith("emoji:"), _state_name(ScriptCreateFSM.emoji_policy)),
    (lambda data: data.startswith("workhours:"), _state_name(ScriptCreateFSM.working_hours)),
    (lambda data: data.startswith("script:"), _state_name(ScriptCreateFSM.confirm)),
    (lambda data: data.startswith("sdedit:"), _state_name(ScriptCreateFSM.confirm)),
    (lambda data: data.startswith("csv:"), _state_name(CSVImportFSM.preview)),
    (lambda data: data.startswith("campaign_script:"), _state_name(CampaignCreateFSM.select_script)),
    (lambda data: data.startswith("campaign_select:"), _state_name(CampaignCreateFSM.select_script)),
    (lambda data: data.startswith("preview:"), _state_name(CampaignCreateFSM.preview)),
    (lambda data: data.startswith("campaign:"), _state_name(CampaignCreateFSM.confirm)),
    (lambda data: data.startswith("discover_confirm:"), _state_name(DiscoverFSM.confirm)),
    (lambda data: data.startswith("startcamp:"), _state_name(CampaignStartFSM.selecting)),
]


class NavigationOverrideMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, types.Message):
            state: FSMContext | None = data.get("state")
            if state and await state.get_state():
                if await _dispatch_navigation_override(event, state):
                    return None
        return await handler(event, data)


class CallbackStateGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, types.CallbackQuery):
            callback_data = event.data or ""
            state: FSMContext | None = data.get("state")
            current_state = await state.get_state() if state else None
            for matcher, expected_state in CALLBACK_STATE_REQUIREMENTS:
                if matcher(callback_data) and current_state != expected_state:
                    lang = _admin_lang(event)
                    await event.answer(
                        (
                            "This button no longer belongs to the current step. Open the menu or start again."
                            if lang == LANG_EN
                            else "Эта кнопка уже не относится к текущему шагу. Откройте меню или начните заново."
                        ),
                        show_alert=True,
                    )
                    if event.message:
                        await event.message.answer(
                            (
                                "I did not run that stale action, so the current flow stays intact."
                                if lang == LANG_EN
                                else "Я не стал выполнять устаревшее действие, чтобы не сломать текущий сценарий."
                            ),
                            reply_markup=_main_menu_keyboard(lang),
                        )
                    return None
        return await handler(event, data)


@router.message(F.text.in_(set(MENU_HANDLERS.keys())))
async def handle_menu_button(message: types.Message, state: FSMContext):
    handler = MENU_HANDLERS[message.text]
    if message.text in STATEFUL_MENU_BUTTONS:
        await handler(message, state)
    else:
        await handler(message)


@router.callback_query()
async def handle_unknown_callback(callback: types.CallbackQuery):
    lang = _admin_lang(callback)
    await callback.answer(
        "Unknown button. Open /start or /help."
        if lang == LANG_EN
        else "Не понял кнопку. Откройте /start или /help.",
        show_alert=True,
    )
    if callback.message:
        try:
            await callback.message.answer(
                (
                    "This button is stale or does not belong to the current step. "
                    "Open the main menu and choose an action again."
                    if lang == LANG_EN
                    else "Эта кнопка устарела или не относится к текущему шагу. "
                    "Откройте главное меню и выберите действие заново."
                ),
                reply_markup=_main_menu_keyboard(lang),
            )
        except Exception:
            logger.warning("Failed to send unknown callback fallback", exc_info=True)


@router.message()
async def handle_unknown_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    lang = _admin_lang(message)
    if lang == LANG_EN:
        text = (
            "A setup wizard is active.\n\n"
            "Answer the last question, press a button above, type back, or use /cancel."
            if current_state
            else "I did not understand that command.\n\n"
            "Use the menu below or /help.\n\n"
            "Usual flow: describe a business, upload contacts, review the first message, and launch."
        )
    else:
        text = ACTIVE_WIZARD_REPLY if current_state else UNKNOWN_ADMIN_REPLY
    await message.answer(text, reply_markup=_main_menu_keyboard(lang))


async def _notify_admin_error(update: types.Update) -> bool:
    callback = getattr(update, "callback_query", None)
    if callback:
        lang = _admin_lang(callback)
        try:
            await callback.answer(
                "Something went wrong. Open /start."
                if lang == LANG_EN
                else "Что-то пошло не так. Откройте /start.",
                show_alert=True,
            )
        except Exception:
            logger.warning("Failed to answer callback after admin bot error", exc_info=True)

        message = getattr(callback, "message", None)
        if message:
            try:
                await message.answer(
                    ADMIN_ERROR_REPLY_EN if lang == LANG_EN else ADMIN_ERROR_REPLY,
                    reply_markup=_main_menu_keyboard(lang),
                )
                return True
            except Exception:
                logger.warning("Failed to send callback error fallback", exc_info=True)

    message = (
        getattr(update, "message", None)
        or getattr(update, "edited_message", None)
        or getattr(update, "business_message", None)
    )
    if message:
        lang = _admin_lang(message)
        try:
            await message.answer(
                ADMIN_ERROR_REPLY_EN if lang == LANG_EN else ADMIN_ERROR_REPLY,
                reply_markup=_main_menu_keyboard(lang),
            )
            return True
        except Exception:
            logger.warning("Failed to send message error fallback", exc_info=True)

    return False


@router.errors()
async def handle_admin_error(event: types.ErrorEvent):
    logger.error(
        "Admin bot handler failed",
        exc_info=(
            type(event.exception),
            event.exception,
            event.exception.__traceback__,
        ),
    )
    await _notify_admin_error(event.update)
    return True


router.message.outer_middleware(NavigationOverrideMiddleware())
router.callback_query.outer_middleware(CallbackStateGuardMiddleware())
dp.include_router(router)


async def start_bot():
    global _bot, _polling_active
    if not is_admin_bot_configured():
        logger.warning("ADMIN_BOT_TOKEN is not configured, bot will not start.")
        return
    bot = _get_bot()
    logger.info("Starting admin bot polling")
    try:
        await dp.start_polling(
            bot,
            handle_signals=False,
            close_bot_session=True,
        )
    finally:
        _polling_active = False
        _bot = None
        logger.info("Admin bot polling task finished")


async def stop_bot():
    global _bot, _polling_active
    _polling_active = False
    if _bot is not None:
        await _bot.session.close()
        _bot = None
