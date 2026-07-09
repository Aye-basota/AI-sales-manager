import asyncio
import logging
from datetime import datetime, time as dt_time, timezone
from collections.abc import Awaitable, Callable
from typing import Any, List
from uuid import UUID

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, KeyboardButton, ReplyKeyboardMarkup
from aiogram.types.base import TelegramObject
from sqlalchemy import select, func, delete
from types import SimpleNamespace

from app.config import get_settings
from app.config.telegram import is_configured_bot_token
from app.core.funnel import get_first_stage, get_max_length_for_stage
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
dp = Dispatcher(storage=MemoryStorage())
router = Router()

MENU_SCRIPTS = "🧩 Сценарии"
MENU_NEW_SCRIPT = "➕ Новый сценарий"
MENU_CAMPAIGNS = "📣 Кампании"
MENU_START_CAMPAIGN = "🚀 Запуск кампании"
MENU_UPLOAD = "📤 Импорт контактов"
MENU_DISCOVER = "🔎 Поиск лидов"
MENU_HOT_LEADS = "🔥 Горячие лиды"
MENU_HELP = "❓ Помощь"
MENU_CONVERSATIONS = "💬 Диалоги"
MENU_ANALYTICS = "📊 Аналитика"

UNKNOWN_ADMIN_REPLY = (
    "Не понял команду.\n\n"
    "Откройте меню ниже или напишите /help.\n\n"
    "Обычный путь: сначала создайте сценарий, затем добавьте контакты, "
    "запустите кампанию и смотрите ответы в горячих лидах и диалогах."
)
ACTIVE_WIZARD_REPLY = (
    "Сейчас открыт мастер настройки.\n\n"
    "Ответьте на последний вопрос, нажмите кнопку в сообщении выше или напишите "
    "/cancel, чтобы вернуться в главное меню."
)
ADMIN_ERROR_REPLY = (
    "Что-то пошло не так, но бот не упал молча.\n\n"
    "Попробуйте открыть /start или /help. Ошибка записана в логи, чтобы ее можно "
    "было быстро разобрать."
)

TONE_OPTIONS = ["Деловой", "Дружелюбный", "Агрессивный"]
TONE_MAP = {
    "Деловой": "professional",
    "Дружелюбный": "friendly",
    "Агрессивный": "aggressive",
}


COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="help", description="Помощь и схема"),
    BotCommand(command="cancel", description="Отменить текущий мастер"),
    BotCommand(command="scripts", description="Список скриптов"),
    BotCommand(command="campaigns", description="Список кампаний"),
    BotCommand(command="upload", description="Импорт контактов"),
    BotCommand(command="analytics", description="Аналитика"),
    BotCommand(command="hotleads", description="Горячие лиды"),
    BotCommand(command="newscript", description="Создать скрипт"),
    BotCommand(command="startcampaign", description="Запустить кампанию"),
    BotCommand(command="discover", description="Поиск лидов"),
    BotCommand(command="conversations", description="История по contact_id"),
]


def _main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_SCRIPTS), KeyboardButton(text=MENU_NEW_SCRIPT)],
            [KeyboardButton(text=MENU_CAMPAIGNS), KeyboardButton(text=MENU_START_CAMPAIGN)],
            [KeyboardButton(text=MENU_UPLOAD), KeyboardButton(text=MENU_DISCOVER)],
            [KeyboardButton(text=MENU_HOT_LEADS), KeyboardButton(text=MENU_CONVERSATIONS)],
            [KeyboardButton(text=MENU_ANALYTICS), KeyboardButton(text=MENU_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие",
    )


@dp.startup()
async def on_startup(bot: Bot):
    global _polling_active
    try:
        await asyncio.wait_for(bot.set_my_commands(COMMANDS), timeout=10)
    except Exception:
        logger.warning("Failed to set admin bot commands during startup", exc_info=True)
    _polling_active = True
    logger.info("Admin bot polling startup completed")


@dp.shutdown()
async def on_shutdown(bot: Bot):
    global _polling_active
    _polling_active = False
    logger.info("Admin bot polling shutdown completed")


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


def _format_scripts(scripts: List) -> str:
    lines = []
    for item in scripts:
        try:
            s, campaign_count = item[0], item[1]
        except Exception:
            s, campaign_count = item, 0
        status = "✅" if s.is_active else "❌"
        lines.append(
            f"{status} <b>{s.name}</b>\n"
            f"Кампаний с этим сценарием: {campaign_count}\n"
            f"Цель: {s.goal}\n"
            f"Максимум сообщений: {s.max_messages} | Тон: {s.tone}"
        )
    return "\n\n".join(lines)


def _format_campaigns(campaigns: List) -> str:
    lines = []
    for item in campaigns:
        try:
            c, script = item[0], item[1]
        except Exception:
            c, script = item, None
        script_name = script.name if script else "—"
        lines.append(
            f"📢 <b>{c.name}</b>\n"
            f"Сценарий: {script_name}\n"
            f"Статус: {c.status}\n"
            f"Контакты: {c.processed_contacts}/{c.total_contacts}\n"
            f"Ответили: {c.replied_count} | Квалифицированы: {c.qualified_count} | Встречи: {c.meeting_booked_count}"
        )
    return "\n\n".join(lines)


def _build_campaign_buttons(campaign) -> list:
    """Return action buttons appropriate for the campaign status."""
    status = campaign.status
    name = campaign.name[:18]

    if status == "draft":
        return [
            types.InlineKeyboardButton(
                text=f"▶️ {name}", callback_data=f"camp_start:{campaign.id}"
            ),
            types.InlineKeyboardButton(
                text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}"
            ),
        ]
    elif status == "running":
        return [
            types.InlineKeyboardButton(
                text=f"⏸ {name}", callback_data=f"camp_pause:{campaign.id}"
            ),
            types.InlineKeyboardButton(
                text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}"
            ),
        ]
    elif status == "paused":
        return [
            types.InlineKeyboardButton(
                text=f"▶️ {name}", callback_data=f"camp_resume:{campaign.id}"
            ),
            types.InlineKeyboardButton(
                text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}"
            ),
        ]
    else:
        return [
            types.InlineKeyboardButton(
                text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}"
            )
        ]


def _build_script_buttons(scripts: List) -> types.InlineKeyboardMarkup:
    rows = [
        [types.InlineKeyboardButton(text="➕ Новый сценарий", callback_data="script_new")]
    ]
    for item in scripts:
        try:
            script, campaign_count = item[0], item[1]
        except Exception:
            script, campaign_count = item, 0

        name = (script.name or "Script")[:18]
        toggle_text = "⏸ Выключить" if script.is_active else "▶️ Включить"
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
                    text=f"🗑 {name}",
                    callback_data=f"script_delete:{script.id}:{campaign_count}",
                )
            ]
        )

    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _format_hotleads(rows: List) -> str:
    lines = []
    for idx, (conv, contact) in enumerate(rows, 1):
        name = contact.telegram_username or contact.phone or str(contact.id)[:8]
        state_emoji = "🔥" if conv.current_state == "hot" else "📅"
        lines.append(
            f"{idx}. {state_emoji} <b>{name}</b>\n"
            f"Статус: {conv.current_state}\n"
            f"Настроение: {conv.sentiment or 'N/A'}"
        )
    return "\n\n".join(lines)


def _format_analytics(
    total_contacts: int,
    sent: int,
    replied: int,
    hot: int,
    meetings: int,
    rejected: int = 0,
    avg_length: float = 0.0,
) -> str:
    reply_rate = (replied / sent * 100) if sent else 0
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
    welcome = (
        "AI Sales Manager готов к работе.\n\n"
        "Как устроен запуск:\n"
        "1. Сценарий — как бот будет говорить с лидами.\n"
        "2. Контакты — кого добавляем через файл или поиск.\n"
        "3. Кампания — какой сценарий отправляем каким контактам.\n"
        "4. Горячие лиды и диалоги — где смотреть ответы.\n\n"
        "Выберите действие в меню ниже. Если застряли, напишите /help."
    )
    await message.answer(welcome, reply_markup=_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "Короткая схема:\n\n"
        "Сценарий отвечает на вопрос: что и каким тоном пишет бот.\n"
        "Контакты отвечают на вопрос: кому писать.\n"
        "Кампания связывает сценарий и контакты, а затем запускает рассылку.\n"
        "Горячие лиды и диалоги показывают, кто ответил и что происходит дальше.\n\n"
        "Основные команды:\n"
        "/start — главное меню\n"
        "/cancel — отменить текущий мастер настройки\n"
        "/help — помощь\n"
        "/scripts — сценарии\n"
        "/newscript — создать сценарий\n"
        "/campaigns — кампании\n"
        "/startcampaign — запустить черновик кампании\n"
        "/upload — импорт контактов\n"
        "/discover — поиск лидов\n"
        "/analytics — аналитика\n"
        "/hotleads — горячие лиды\n"
        "/conversations [contact_id] — последние диалоги или история контакта"
    )
    await message.answer(text, reply_markup=_main_menu_keyboard())


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Активного мастера нет. Выберите действие в меню ниже.",
            reply_markup=_main_menu_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        "Ок, остановил текущий мастер. Возвращаю в главное меню.",
        reply_markup=_main_menu_keyboard(),
    )


@router.message(Command("scripts"))
async def cmd_scripts(message: types.Message):
    await _send_or_edit_scripts(message)


async def _load_scripts_with_campaign_counts():
    async with AsyncSessionLocal() as session:
        campaign_count = (
            select(func.count(Campaign.id))
            .where(Campaign.script_id == Script.id)
            .scalar_subquery()
        )
        result = await session.execute(
            select(Script, campaign_count).order_by(Script.created_at.desc()).limit(20)
        )
        return result.all()


async def _send_or_edit_scripts(message: types.Message):
    scripts = await _load_scripts_with_campaign_counts()

    if not scripts:
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="➕ Новый сценарий", callback_data="script_new"
                    )
                ]
            ]
        )
        text = (
            "Сценариев пока нет. Создайте первый сценарий, чтобы бот понимал, "
            "как общаться с лидами."
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

    text = _format_scripts(scripts)
    kb = _build_script_buttons(scripts)
    if message.from_user and message.from_user.is_bot:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "refresh_scripts")
async def refresh_scripts(callback: types.CallbackQuery):
    await cmd_scripts(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data == "script_new")
async def handle_script_new(callback: types.CallbackQuery, state: FSMContext):
    await cmd_newscript(callback.message, state)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("script_toggle:"))
async def handle_script_toggle(callback: types.CallbackQuery):
    try:
        script_id = UUID(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            await callback.answer("❌ Скрипт не найден")
            return
        script.is_active = not script.is_active
        await session.commit()

    await callback.answer("✅ Обновлено")
    await cmd_scripts(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("script_delete:"))
async def handle_script_delete(callback: types.CallbackQuery):
    try:
        parts = callback.data.split(":")
        script_id = UUID(parts[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        campaign_count_result = await session.execute(
            select(func.count(Campaign.id)).where(Campaign.script_id == script_id)
        )
        campaign_count = campaign_count_result.scalar() or 0
        if campaign_count:
            await callback.answer("❌ Скрипт используется в кампаниях")
            return

        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()
        if not script:
            await callback.answer("❌ Скрипт не найден")
            return
        await session.delete(script)
        await session.commit()

    await callback.answer("🗑 Скрипт удалён")
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
    campaigns = await _load_campaigns()

    if not campaigns:
        text = (
            "Кампаний пока нет.\n\n"
            "Сначала добавьте контакты через импорт или поиск, затем выберите сценарий "
            "и запустите кампанию."
        )
        kb = types.InlineKeyboardMarkup(inline_keyboard=[])
    else:
        text = _format_campaigns(campaigns)
        kb_rows = []
        for row in campaigns:
            campaign = row[0]
            kb_rows.append(_build_campaign_buttons(campaign))
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
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if campaign and campaign.status == "running":
            campaign.status = "paused"
            await session.commit()
            await callback.answer("⏸ Пауза")
        else:
            await callback.answer("❌ Нельзя поставить на паузу")
    await _send_or_edit_campaigns(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("camp_resume:"))
async def handle_camp_resume(callback: types.CallbackQuery):
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if campaign and campaign.status == "paused":
            campaign.status = "running"
            await session.commit()
            await callback.answer("▶️ Возобновлено")
        else:
            await callback.answer("❌ Нельзя возобновить")
    await _send_or_edit_campaigns(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("camp_start:"))
async def handle_camp_start(callback: types.CallbackQuery):
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if campaign and campaign.status == "draft":
            campaign.status = "running"
            campaign.started_at = datetime.now(timezone.utc)
            await session.commit()
            await callback.answer("▶️ Запущено")
            from app.core.scheduler import process_campaigns

            _schedule_process_campaign(campaign.id, process_campaigns)
        else:
            await callback.answer("❌ Кампания уже запущена или не найдена")
    await _send_or_edit_campaigns(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("camp_delete:"))
async def handle_camp_delete(callback: types.CallbackQuery):
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID")
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
            await callback.answer("🗑 Удалено")
        else:
            await callback.answer("❌ Кампания не найдена")
    await _send_or_edit_campaigns(callback.message)


@router.message(Command("analytics"))
async def cmd_analytics(message: types.Message):
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
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📋 Экспорт в CSV", callback_data="export_analytics"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🔄 Refresh", callback_data="refresh_analytics"
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
        caption="📋 Аналитика по кампаниям",
    )
    await callback.answer("📋 Файл отправлен")


@router.message(Command("hotleads"))
async def cmd_hotleads(message: types.Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation, Contact)
            .join(Contact, Conversation.contact_id == Contact.id)
            .where(Conversation.current_state.in_(["hot", "meeting_booked"]))
            .order_by(Conversation.last_message_at.desc())
            .limit(20)
        )
        rows = result.all()

    if not rows:
        await message.answer(
            "Горячих лидов пока нет.\n\n"
            "Когда лид проявит интерес или согласится на встречу, он появится здесь."
        )
        return

    text = _format_hotleads(rows)
    kb_rows = []
    for conv, contact in rows:
        kb_rows.append(
            [
                types.InlineKeyboardButton(
                    text="✅ Qualified", callback_data=f"qualify:{conv.id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Rejected", callback_data=f"reject:{conv.id}"
                ),
                types.InlineKeyboardButton(
                    text="📜 История диалога", callback_data=f"history:{conv.id}"
                ),
            ]
        )
        kb_rows.append(
            [
                types.InlineKeyboardButton(
                    text="📋 Диалог", callback_data=f"dialog:{conv.id}"
                )
            ]
        )
    kb_rows.append(
        [
            types.InlineKeyboardButton(
                text="🔄 Refresh", callback_data="refresh_hotleads"
            )
        ]
    )
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "refresh_hotleads")
async def refresh_hotleads(callback: types.CallbackQuery):
    await cmd_hotleads(callback.message)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("qualify:"))
async def handle_qualify(callback: types.CallbackQuery):
    conv_id_str = callback.data.split(":", 1)[1]
    try:
        conv_id = UUID(conv_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID диалога")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.operator_status = "qualified"
            await session.commit()
            await callback.answer("✅ Статус обновлен: Qualified")
        else:
            await callback.answer("❌ Диалог не найден")


@router.callback_query(lambda c: c.data and c.data.startswith("reject:"))
async def handle_reject(callback: types.CallbackQuery):
    conv_id_str = callback.data.split(":", 1)[1]
    try:
        conv_id = UUID(conv_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID диалога")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.operator_status = "rejected"
            await session.commit()
            await callback.answer("❌ Статус обновлен: Rejected")
        else:
            await callback.answer("❌ Диалог не найден")


@router.callback_query(lambda c: c.data and c.data.startswith("dialog:"))
async def handle_dialog(callback: types.CallbackQuery):
    conv_id_str = callback.data.split(":", 1)[1]
    try:
        conv_id = UUID(conv_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID диалога")
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
        await callback.message.answer("Сообщений в диалоге не найдено.")
        await callback.answer()
        return

    lines = []
    for msg in messages:
        sender = "👤" if msg.direction == "inbound" else "🤖"
        lines.append(f"{sender} {msg.content}")

    text = "\n\n".join(lines)
    await callback.message.answer(text)
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
    conv_id_str = callback.data.split(":", 1)[1]
    try:
        conv_id = UUID(conv_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID диалога")
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
        await callback.message.answer("Сообщений в диалоге не найдено.")
        await callback.answer()
        return

    text = _format_history_messages(messages)
    for chunk in _split_long_text(text):
        await callback.message.answer(chunk)
    await callback.answer()


@router.message(Command("conversations"))
async def cmd_conversations(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await _send_recent_conversations(message)
        return

    try:
        contact_id = UUID(args[1].strip())
    except ValueError:
        await message.answer("Неверный формат contact_id. Ожидается UUID.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.contact_id == contact_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            await message.answer("Диалог для данного контакта не найден.")
            return

        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.sent_at.asc())
        )
        messages = result.scalars().all()

    if not messages:
        await message.answer("В диалоге пока нет сообщений.")
        return

    lines = []
    for msg in messages:
        sender = "👤" if msg.direction == "inbound" else "🤖"
        lines.append(f"{sender} {msg.content}")

    text = "\n\n".join(lines)
    await message.answer(text)


async def _send_recent_conversations(message: types.Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversation, Contact)
            .join(Contact, Conversation.contact_id == Contact.id)
            .order_by(Conversation.last_message_at.desc())
            .limit(10)
        )
        rows = result.all()

    if not rows:
        await message.answer(
            "Диалогов пока нет.\n\n"
            "Они появятся здесь, когда лиды начнут отвечать. Если нужен конкретный "
            "контакт, используйте /conversations <contact_id>."
        )
        return

    lines = []
    kb_rows = []
    for idx, (conversation, contact) in enumerate(rows, 1):
        name = (
            contact.telegram_username
            or f"{contact.first_name or ''} {contact.last_name or ''}".strip()
            or contact.phone
            or str(contact.id)
        )
        lines.append(
            f"{idx}. <b>{name}</b>\n"
            f"Статус: {conversation.current_state}\n"
            f"contact_id: <code>{contact.id}</code>"
        )
        kb_rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"📜 История {idx}", callback_data=f"history:{conversation.id}"
                )
            ]
        )

    await message.answer(
        "Последние диалоги:\n\n" + "\n\n".join(lines),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# FSM: Create Script
# ---------------------------------------------------------------------------


@router.message(Command("newscript"))
async def cmd_newscript(message: types.Message, state: FSMContext):
    await state.set_state(ScriptCreateFSM.name)
    await message.answer("📝 Создание нового скрипта.\n\nВведите название скрипта:")


@router.message(ScriptCreateFSM.name)
async def process_script_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(ScriptCreateFSM.role_prompt)
    await message.answer(
        "Введите роль (role_prompt), например:\n'Ты менеджер по продажам MedTech решений.'"
    )


@router.message(ScriptCreateFSM.role_prompt)
async def process_script_role(message: types.Message, state: FSMContext):
    await state.update_data(role_prompt=message.text)
    await state.set_state(ScriptCreateFSM.target_audience)
    await message.answer(
        "Введите целевую аудиторию (или отправьте '-' чтобы пропустить):"
    )


@router.message(ScriptCreateFSM.target_audience)
async def process_script_audience(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(target_audience=None if text == "-" else text)
    await state.set_state(ScriptCreateFSM.goal)
    await message.answer(
        "Введите цель диалога (goal), например:\n'Назначить демонстрацию продукта'"
    )


@router.message(ScriptCreateFSM.goal)
async def process_script_goal(message: types.Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.set_state(ScriptCreateFSM.success_criteria)
    await message.answer("Введите критерий успеха (или '-' чтобы пропустить):")


@router.message(ScriptCreateFSM.success_criteria)
async def process_script_criteria(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(success_criteria=None if text == "-" else text)
    await state.set_state(ScriptCreateFSM.tone)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=t, callback_data=f"tone:{t}")]
            for t in TONE_OPTIONS
        ]
    )
    await message.answer("Выберите тональность:", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("tone:"))
async def process_script_tone(callback: types.CallbackQuery, state: FSMContext):
    tone_label = callback.data.split(":", 1)[1]
    tone_value = TONE_MAP.get(tone_label, "professional")
    await state.update_data(tone=tone_value)
    await state.set_state(ScriptCreateFSM.first_message_goal)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Hook (мягкий контакт)", callback_data="fmg:hook"
                ),
                types.InlineKeyboardButton(
                    text="Qualification (вопрос)", callback_data="fmg:qualification"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="Value (ценность)", callback_data="fmg:value"
                ),
                types.InlineKeyboardButton(
                    text="Call (сразу созвон)", callback_data="fmg:cta"
                ),
            ],
        ]
    )
    await callback.message.answer("Выберите цель первого сообщения:", reply_markup=kb)
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
    await state.update_data(call_to_action=message.text)
    await state.set_state(ScriptCreateFSM.language)
    await message.answer("Введите язык сообщений (ru / en):")


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
                    text="Запрещены", callback_data="emoji:forbidden"
                )
            ],
            [types.InlineKeyboardButton(text="Редко", callback_data="emoji:rare")],
            [
                types.InlineKeyboardButton(
                    text="Разрешены", callback_data="emoji:allowed"
                )
            ],
        ]
    )
    await message.answer("Политика использования эмодзи:", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("emoji:"))
async def process_script_emoji_policy(callback: types.CallbackQuery, state: FSMContext):
    policy = callback.data.split(":", 1)[1]
    await state.update_data(emoji_policy=policy)
    await state.set_state(ScriptCreateFSM.max_first_message_length)
    await callback.message.answer(
        "Введите максимальную длину первого сообщения в символах (например, 200):"
    )
    await callback.answer()


@router.message(ScriptCreateFSM.max_first_message_length)
async def process_script_max_first_message_length(
    message: types.Message, state: FSMContext
):
    try:
        val = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    await state.update_data(max_first_message_length=val)
    await state.set_state(ScriptCreateFSM.max_messages)
    await message.answer(
        "Введите максимальное количество сообщений на контакт (например, 2):"
    )


@router.message(ScriptCreateFSM.max_messages)
async def process_script_max_messages(message: types.Message, state: FSMContext):
    try:
        val = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    await state.update_data(max_messages=val)
    await state.set_state(ScriptCreateFSM.follow_up_delay_hours)
    await message.answer("Введите задержку follow-up в часах (например, 24):")


@router.message(ScriptCreateFSM.follow_up_delay_hours)
async def process_script_delay(message: types.Message, state: FSMContext):
    try:
        val = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    await state.update_data(follow_up_delay_hours=val)
    await state.set_state(ScriptCreateFSM.working_hours)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Подтвердить 09:00-18:00", callback_data="workhours:default"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📝 Указать вручную", callback_data="workhours:manual"
                )
            ],
        ]
    )
    await message.answer(
        "Рабочие часы по умолчанию: 09:00 - 18:00.\nЧто выберете?",
        reply_markup=kb,
    )


@router.callback_query(lambda c: c.data == "workhours:default")
async def process_work_hours_default(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(working_hours_start=dt_time(9, 0))
    await state.update_data(working_hours_end=dt_time(18, 0))
    await state.set_state(ScriptCreateFSM.timezone)
    await callback.message.answer("Введите timezone (по умолчанию Europe/Moscow):")
    await callback.answer()


@router.callback_query(lambda c: c.data == "workhours:manual")
async def process_work_hours_manual(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ScriptCreateFSM.working_hours)
    await callback.message.answer(
        "Введите начало рабочих часов (HH:MM, например 09:00):"
    )
    await callback.answer()


@router.message(ScriptCreateFSM.working_hours)
async def process_script_work_start(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split("-")
        if len(parts) == 2:
            start_str, end_str = parts[0].strip(), parts[1].strip()
            h1, m1 = map(int, start_str.split(":"))
            h2, m2 = map(int, end_str.split(":"))
            await state.update_data(working_hours_start=dt_time(h1, m1))
            await state.update_data(working_hours_end=dt_time(h2, m2))
            await state.set_state(ScriptCreateFSM.timezone)
            await message.answer("Введите timezone (по умолчанию Europe/Moscow):")
        else:
            start_str = message.text.strip()
            await state.update_data(_start_tmp=start_str)
            await state.set_state(ScriptCreateFSM.working_hours_end)
            await message.answer("Введите конец рабочих часов (HH:MM, например 18:00):")
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите HH:MM-HH:MM или два отдельных значения."
        )


@router.message(ScriptCreateFSM.working_hours_end)
async def process_script_work_end(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        start_str = data.get("_start_tmp")
        end_str = message.text.strip()
        h1, m1 = map(int, start_str.split(":"))
        h2, m2 = map(int, end_str.split(":"))
        await state.update_data(working_hours_start=dt_time(h1, m1))
        await state.update_data(working_hours_end=dt_time(h2, m2))
        await state.set_state(ScriptCreateFSM.timezone)
        await message.answer("Введите timezone (по умолчанию Europe/Moscow):")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите время в формате HH:MM.")


@router.message(ScriptCreateFSM.timezone)
async def process_script_timezone(message: types.Message, state: FSMContext):
    tz = normalize_timezone(message.text.strip() or "Europe/Moscow")
    await state.update_data(timezone=tz)
    await state.set_state(ScriptCreateFSM.confirm)
    data = await state.get_data()
    summary = (
        f"📋 Проверьте данные скрипта:\n\n"
        f"Название: {data['name']}\n"
        f"Роль: {data['role_prompt']}\n"
        f"Аудитория: {data.get('target_audience') or '—'}\n"
        f"Цель: {data['goal']}\n"
        f"Критерий успеха: {data.get('success_criteria') or '—'}\n"
        f"Тон: {data['tone']}\n"
        f"Первое сообщение: {data.get('first_message_goal', 'hook')}\n"
        f"Призыв к действию: {data.get('call_to_action', '15-минутный созвон')}\n"
        f"Язык: {data.get('language', 'ru')}\n"
        f"Эмодзи: {data.get('emoji_policy', 'forbidden')}\n"
        f"Макс. длина первого сообщения: {data.get('max_first_message_length', 200)}\n"
        f"Max messages: {data['max_messages']}\n"
        f"Follow-up delay: {data['follow_up_delay_hours']}ч\n"
        f"Рабочие часы: {data['working_hours_start']} - {data['working_hours_end']}\n"
        f"Timezone: {data.get('timezone', '—')}\n\n"
        f"Создать скрипт?"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Создать", callback_data="script:create"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отмена", callback_data="script:cancel"
                )
            ],
        ]
    )
    await message.answer(summary, reply_markup=kb)


@router.callback_query(lambda c: c.data == "script:create")
async def confirm_create_script(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        script = Script(
            name=data["name"],
            role_prompt=data["role_prompt"],
            target_audience=data.get("target_audience"),
            goal=data["goal"],
            success_criteria=data.get("success_criteria"),
            tone=data.get("tone", "professional"),
            first_message_goal=data.get("first_message_goal", "hook"),
            call_to_action=data.get("call_to_action", "15-минутный созвон"),
            language=data.get("language", "ru"),
            emoji_policy=data.get("emoji_policy", "forbidden"),
            max_first_message_length=data.get("max_first_message_length", 200),
            max_messages=data.get("max_messages", 2),
            follow_up_delay_hours=data.get("follow_up_delay_hours", 24),
            working_hours_start=data["working_hours_start"],
            working_hours_end=data["working_hours_end"],
            timezone=data.get("timezone", "Europe/Moscow"),
            is_active=True,
        )
        session.add(script)
        await session.commit()
        await session.refresh(script)
    await state.clear()
    await callback.answer("✅ Скрипт создан!")
    await callback.message.answer(
        f"Скрипт <b>{script.name}</b> создан.", parse_mode="HTML"
    )


@router.callback_query(lambda c: c.data == "script:cancel")
async def cancel_create_script(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("❌ Создание отменено")
    await callback.message.answer("Создание скрипта отменено.")


# ---------------------------------------------------------------------------
# FSM: Import CSV / Excel
# ---------------------------------------------------------------------------


@router.message(Command("upload"))
async def cmd_upload(message: types.Message, state: FSMContext):
    await state.set_state(CSVImportFSM.waiting_file)
    await message.answer(
        "📎 Отправьте CSV или Excel-файл с контактами.\n\n"
        "Обязательная колонка: telegram_user_id (или telegram_id).\n\n"
        "Если открыли импорт случайно, выберите другой раздел в меню или напишите /cancel.\n\n"
        "Пример CSV:\n"
        "first_name,last_name,company_name,position,city,industry,telegram_user_id,phone\n"
        "Иван,Иванов,ООО Ромашка,Директор,Москва,IT,123456789,+79990000000",
        reply_markup=_main_menu_keyboard(),
    )


@router.message(CSVImportFSM.waiting_file)
async def process_upload_file(message: types.Message, state: FSMContext):
    if not message.document:
        await message.answer(
            "❌ Пожалуйста, отправьте файл. Чтобы выйти, выберите другой раздел в меню "
            "или напишите /cancel.",
            reply_markup=_main_menu_keyboard(),
        )
        return

    file_name = message.document.file_name.lower()
    if not (file_name.endswith(".csv") or file_name.endswith((".xlsx", ".xls"))):
        await message.answer("❌ Принимаются только CSV и Excel файлы.")
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
            await message.answer(f"❌ {error_text}. Проверьте файл и попробуйте снова.")
        else:
            await message.answer(f"❌ Ошибка парсинга: {exc}")
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

    text = (
        f"📊 Найдено {len(records)} контактов.\n\n"
        f"Первые {len(preview)}:\n{preview_text}\n\n"
        f"Что делаем?"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Создать кампанию", callback_data="csv:create_campaign"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отмена", callback_data="csv:cancel"
                ),
            ]
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data == "csv:cancel")
async def cancel_csv_import(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("❌ Импорт отменен")
    await callback.message.answer("Импорт отменен.")


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
    data = await state.get_data()
    records = data.get("records", [])
    if not records:
        await callback.answer("❌ Нет контактов")
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
            "❌ Нет активных скриптов. Сначала создайте скрипт через /newscript",
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
                text="❌ Отмена", callback_data="campaign_select:cancel"
            )
        ]
    )
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await _send_or_edit_callback_message(
        callback,
        "Выберите скрипт для кампании.\n\n"
        "После выбора я пересоберу предпросмотр первого сообщения.",
        reply_markup=kb,
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# FSM: Campaign creation from import / discover
# ---------------------------------------------------------------------------


def _preview_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Запустить", callback_data="preview:launch"
                ),
                types.InlineKeyboardButton(
                    text="🔄 Перегенерировать", callback_data="preview:regenerate"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="✏️ Изменить скрипт", callback_data="preview:change_script"
                )
            ],
        ]
    )


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
            return build_safe_initial_fallback(contact)
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
            return build_safe_initial_fallback(contact)
        return text
    except Exception:
        logger.exception("Failed to generate campaign preview")
        return build_safe_initial_fallback(contact)


@router.callback_query(lambda c: c.data and c.data.startswith("campaign_script:"))
async def process_campaign_script(callback: types.CallbackQuery, state: FSMContext):
    script_id_str = callback.data.split(":", 1)[1]
    try:
        script_id = UUID(script_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID скрипта")
        await state.clear()
        return

    data = await state.get_data()
    records = data.get("records", [])
    if not records:
        await callback.answer("❌ Нет контактов")
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()

    if not script:
        await callback.answer("❌ Скрипт не найден")
        await state.clear()
        return

    await state.update_data(script_id=script_id)
    preview_text = await _generate_preview_message(script, records[0])
    await state.update_data(preview_text=preview_text)
    await state.set_state(CampaignCreateFSM.preview)

    text = f"👁 Предпросмотр первого сообщения:\n\n{preview_text}"
    await _send_or_edit_callback_message(
        callback, text, reply_markup=_preview_keyboard()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "preview:regenerate")
async def handle_preview_regenerate(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    script_id = data.get("script_id")
    records = data.get("records", [])
    if not script_id or not records:
        await callback.answer("❌ Сессия устарела")
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()

    if not script:
        await callback.answer("❌ Скрипт не найден")
        await state.clear()
        return

    preview_text = await _generate_preview_message(script, records[0])
    await state.update_data(preview_text=preview_text)
    text = f"👁 Предпросмотр первого сообщения:\n\n{preview_text}"
    try:
        await callback.message.edit_text(text, reply_markup=_preview_keyboard())
    except TelegramBadRequest as exc:
        if not _is_message_not_modified(exc):
            raise
        await callback.answer("Без изменений")
        return
    await callback.answer("🔄 Обновлено")


@router.callback_query(lambda c: c.data == "preview:change_script")
async def handle_preview_change_script(
    callback: types.CallbackQuery, state: FSMContext
):
    await _show_campaign_script_picker(callback, state)


@router.callback_query(lambda c: c.data == "campaign_select:cancel")
async def cancel_campaign_script_selection(
    callback: types.CallbackQuery, state: FSMContext
):
    await state.clear()
    await callback.answer("❌ Отменено")
    await _send_or_edit_callback_message(callback, "Создание кампании отменено.")


@router.callback_query(lambda c: c.data == "preview:launch")
async def handle_preview_launch(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CampaignCreateFSM.name)
    await callback.message.answer("Введите название кампании:")
    await callback.answer()


@router.message(CampaignCreateFSM.name)
async def process_campaign_name(message: types.Message, state: FSMContext):
    await state.update_data(campaign_name=message.text)
    data = await state.get_data()
    await state.set_state(CampaignCreateFSM.confirm)

    script_id = data.get("script_id")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Script).where(Script.id == script_id))
        script = result.scalar_one_or_none()

    text = (
        f"📋 Сводка по кампании:\n\n"
        f"Название: {data['campaign_name']}\n"
        f"Скрипт: {script.name if script else '—'}\n"
        f"Контактов: {len(data.get('records', []))}\n\n"
        f"👁 Предпросмотр первого сообщения:\n{data.get('preview_text', '—')}\n\n"
        f"Запустить?"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="▶️ Запустить", callback_data="campaign:start_now"
                ),
                types.InlineKeyboardButton(
                    text="⏸ Позже", callback_data="campaign:start_later"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отмена", callback_data="campaign:cancel"
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data == "campaign:cancel")
async def cancel_campaign_create(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("❌ Создание отменено")
    await callback.message.answer("Создание кампании отменено.")


@router.callback_query(lambda c: c.data == "campaign:start_later")
async def campaign_start_later(callback: types.CallbackQuery, state: FSMContext):
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

        from app.services.contact_import import upsert_contacts

        created, updated = await upsert_contacts(session, records, source="csv_import")
        contacts = created + updated

        for contact in contacts:
            cc = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="pending",
                message_count=0,
            )
            session.add(cc)

        campaign.total_contacts = len(contacts)
        await session.commit()

    await state.clear()
    await callback.answer("✅ Кампания сохранена как draft")
    await callback.message.answer(
        f"Кампания <b>{campaign.name}</b> сохранена. Запустите через /startcampaign.",
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "campaign:start_now")
async def campaign_start_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    records = data.get("records", [])

    async with AsyncSessionLocal() as session:
        script_id = data.get("script_id")
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

        from app.services.contact_import import upsert_contacts

        created, updated = await upsert_contacts(session, records, source="csv_import")
        contacts = created + updated

        for contact in contacts:
            cc = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="pending",
                message_count=0,
            )
            session.add(cc)

        campaign.total_contacts = len(contacts)
        await session.commit()

    await state.clear()
    await callback.answer("✅ Кампания запущена!")
    await callback.message.answer(
        f"Кампания <b>{campaign.name}</b> запущена с {campaign.total_contacts} контактами.",
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
    await state.set_state(DiscoverFSM.query)
    await message.answer(
        "🔍 Поиск лидов.\n\n"
        "Введите ключевое слово для поиска (например, 'медицинский директор' или название канала):"
    )


class DiscoverFSM(StatesGroup):
    query = State()
    source = State()
    limit = State()
    confirm = State()


@router.message(DiscoverFSM.query)
async def process_discover_query(message: types.Message, state: FSMContext):
    await state.update_data(query=message.text)
    await state.set_state(DiscoverFSM.source)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🔍 Telegram Search", callback_data="discover:telegram_search"
                ),
                types.InlineKeyboardButton(
                    text="📢 Мои каналы", callback_data="discover:channel_parse"
                ),
                types.InlineKeyboardButton(
                    text="🌐 Внешняя база", callback_data="discover:external_api"
                ),
            ]
        ]
    )
    await message.answer("Выберите источник:", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("discover:"))
async def process_discover_source(callback: types.CallbackQuery, state: FSMContext):
    source = callback.data.split(":", 1)[1]
    await state.update_data(source=source)
    await state.set_state(DiscoverFSM.limit)
    await callback.message.answer("Сколько контактов найти? (по умолчанию 20)")
    await callback.answer()


@router.message(DiscoverFSM.limit)
async def process_discover_limit(message: types.Message, state: FSMContext):
    text = message.text.strip()
    try:
        limit = int(text) if text else 20
    except ValueError:
        limit = 20

    await state.update_data(limit=limit)
    data = await state.get_data()
    query = data.get("query", "")
    source = data.get("source", "telegram_search")

    await message.answer(f"⏳ Ищу контакты по запросу '{query}' через {source}...")

    from app.services.lead_discovery import LeadCriteria, discover_leads
    from app.services.lead_validation import validate_and_enrich

    criteria = LeadCriteria(query=query, limit=limit)
    try:
        discovered = await discover_leads(criteria, source=source)
    except Exception as exc:
        logger.exception("Discover failed")
        await message.answer(f"❌ Ошибка при поиске: {exc}")
        await state.clear()
        return

    usernames = [d.telegram_username for d in discovered if d.telegram_username]
    valid_map = {}
    if usernames:
        try:
            valid_map = await validate_and_enrich(usernames)
        except Exception:
            logger.warning("Lead validation failed during discovery", exc_info=True)

    valid_count = sum(1 for d in discovered if d.telegram_username in valid_map)

    results = []
    for d in discovered:
        entry = {
            "telegram_username": d.telegram_username,
            "telegram_user_id": d.telegram_user_id,
            "first_name": d.first_name,
            "last_name": d.last_name,
            "company_name": d.company_name,
            "position": d.position,
            "city": d.city,
            "industry": d.industry,
            "source": d.source,
            "is_valid": "valid" if d.telegram_username in valid_map else "unknown",
        }
        if d.telegram_username in valid_map:
            info = valid_map[d.telegram_username]
            entry["telegram_user_id"] = info.get("user_id")
            entry["first_name"] = entry["first_name"] or info.get("first_name")
            entry["last_name"] = entry["last_name"] or info.get("last_name")
        results.append(entry)

    await state.update_data(discovered=results, records=results)
    await state.set_state(DiscoverFSM.confirm)

    preview_lines = []
    for idx, r in enumerate(results[:5], 1):
        preview_lines.append(
            f"{idx}. @{r['telegram_username']} — {r['first_name'] or ''} {r['last_name'] or ''}"
        )
    preview_text = (
        "\n".join(preview_lines) if preview_lines else "(нет данных для предпросмотра)"
    )

    text = (
        f"Найдено {len(results)} контактов. Валидно {valid_count}.\n\n"
        f"Первые {min(len(results), 5)}:\n{preview_text}\n\n"
        f"Добавить в базу?"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Добавить и создать кампанию",
                    callback_data="discover_confirm:add",
                ),
                types.InlineKeyboardButton(
                    text="📋 Предпросмотр", callback_data="discover_confirm:preview"
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отмена", callback_data="discover_confirm:cancel"
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("discover_confirm:"))
async def process_discover_confirm(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 1)[1]
    data = await state.get_data()
    discovered = data.get("discovered", [])

    if action == "cancel":
        await state.clear()
        await callback.answer("❌ Отменено")
        await callback.message.answer("Поиск отменен.")
        return

    if action == "preview":
        lines = []
        for idx, r in enumerate(discovered, 1):
            lines.append(
                f"{idx}. @{r.get('telegram_username')} — {r.get('first_name') or ''} {r.get('last_name') or ''} "
                f"({r.get('city') or ''}, {r.get('position') or ''})"
            )
        text = "\n".join(lines) if lines else "(пусто)"
        await callback.answer()
        await callback.message.answer(f"📋 Полный список:\n\n{text}")
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
                await callback.answer("❌ Ошибка")
                await callback.message.answer(f"Ошибка сохранения: {exc}")
                return

        await callback.answer("✅ Добавлено!")
        await callback.message.answer(
            f"✅ Сохранено {len(created)} новых и обновлено {len(updated)} контактов.\n"
            f"Теперь создадим кампанию."
        )
        await start_campaign_from_csv(callback, state)
        return

    await callback.answer()


# ---------------------------------------------------------------------------
# FSM: Start Campaign
# ---------------------------------------------------------------------------


@router.message(Command("startcampaign"))
async def cmd_startcampaign(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Campaign)
            .where(Campaign.status == "draft")
            .order_by(Campaign.created_at.desc())
            .limit(20)
        )
        campaigns = result.scalars().all()

    if not campaigns:
        await message.answer("Нет кампаний со статусом draft.")
        return

    await state.set_state(CampaignStartFSM.selecting)
    kb_rows = []
    for c in campaigns:
        kb_rows.append(
            [types.InlineKeyboardButton(text=c.name, callback_data=f"startcamp:{c.id}")]
        )
    kb_rows.append(
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="startcamp:cancel")]
    )
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await message.answer("Выберите кампанию для запуска:", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("startcamp:"))
async def handle_startcamp(callback: types.CallbackQuery, state: FSMContext):
    camp_id_str = callback.data.split(":", 1)[1]
    if camp_id_str == "cancel":
        await state.clear()
        await callback.answer("Отменено")
        await callback.message.answer("Запуск кампании отменен.")
        return

    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if not campaign:
            await callback.answer("❌ Кампания не найдена")
            await state.clear()
            return
        if campaign.status != "draft":
            await callback.answer("❌ Кампания уже не в статусе draft")
            await state.clear()
            return

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
        await callback.answer("⚠️ Кампания запущена, отправка будет повторена")
        await callback.message.answer(
            f"Кампания <b>{campaign.name}</b> запущена, но первая попытка отправки "
            "не завершилась. Планировщик повторит обработку автоматически; ошибка "
            "записана в логи.",
            parse_mode="HTML",
        )
    else:
        await callback.answer("✅ Кампания запущена!")
        await callback.message.answer(
            f"Кампания <b>{campaign.name}</b> запущена.", parse_mode="HTML"
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
    "New Script",
    "Start Campaign",
    "Upload",
    "Discover",
}
COMMAND_HANDLERS = {
    "/start": (cmd_start, False),
    "/help": (cmd_help, False),
    "/cancel": (cmd_cancel, True),
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
            "Неизвестная команда не будет записана как ответ в текущем мастере.\n\n"
            "Используйте меню, /help или /cancel.",
            reply_markup=_main_menu_keyboard(),
        )
        return True

    handler, needs_state = handler_info
    if command != "/cancel":
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
    (lambda data: data.startswith("fmg:"), _state_name(ScriptCreateFSM.first_message_goal)),
    (lambda data: data.startswith("emoji:"), _state_name(ScriptCreateFSM.emoji_policy)),
    (lambda data: data.startswith("workhours:"), _state_name(ScriptCreateFSM.working_hours)),
    (lambda data: data.startswith("script:"), _state_name(ScriptCreateFSM.confirm)),
    (lambda data: data.startswith("csv:"), _state_name(CSVImportFSM.preview)),
    (lambda data: data.startswith("campaign_script:"), _state_name(CampaignCreateFSM.select_script)),
    (lambda data: data.startswith("campaign_select:"), _state_name(CampaignCreateFSM.select_script)),
    (lambda data: data.startswith("preview:"), _state_name(CampaignCreateFSM.preview)),
    (lambda data: data.startswith("campaign:"), _state_name(CampaignCreateFSM.confirm)),
    (lambda data: data.startswith("discover:"), _state_name(DiscoverFSM.source)),
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
                    await event.answer(
                        "Эта кнопка уже не относится к текущему шагу. Откройте меню или начните заново.",
                        show_alert=True,
                    )
                    if event.message:
                        await event.message.answer(
                            "Я не стал выполнять устаревшее действие, чтобы не сломать текущий сценарий.",
                            reply_markup=_main_menu_keyboard(),
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
    await callback.answer("Не понял кнопку. Откройте /start или /help.", show_alert=True)
    if callback.message:
        try:
            await callback.message.answer(
                "Эта кнопка устарела или не относится к текущему шагу. "
                "Откройте главное меню и выберите действие заново.",
                reply_markup=_main_menu_keyboard(),
            )
        except Exception:
            logger.warning("Failed to send unknown callback fallback", exc_info=True)


@router.message()
async def handle_unknown_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    text = ACTIVE_WIZARD_REPLY if current_state else UNKNOWN_ADMIN_REPLY
    await message.answer(text, reply_markup=_main_menu_keyboard())


async def _notify_admin_error(update: types.Update) -> bool:
    callback = getattr(update, "callback_query", None)
    if callback:
        try:
            await callback.answer("Что-то пошло не так. Откройте /start.", show_alert=True)
        except Exception:
            logger.warning("Failed to answer callback after admin bot error", exc_info=True)

        message = getattr(callback, "message", None)
        if message:
            try:
                await message.answer(ADMIN_ERROR_REPLY, reply_markup=_main_menu_keyboard())
                return True
            except Exception:
                logger.warning("Failed to send callback error fallback", exc_info=True)

    message = (
        getattr(update, "message", None)
        or getattr(update, "edited_message", None)
        or getattr(update, "business_message", None)
    )
    if message:
        try:
            await message.answer(ADMIN_ERROR_REPLY, reply_markup=_main_menu_keyboard())
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
