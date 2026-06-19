import asyncio
import logging
from datetime import datetime, time as dt_time, timezone
from typing import List
from uuid import UUID

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, KeyboardButton, ReplyKeyboardMarkup
from sqlalchemy import select, func, delete
from types import SimpleNamespace

from app.config import get_settings
from app.core.funnel import get_first_stage, get_max_length_for_stage
from app.db.session import AsyncSessionLocal
from app.llm.engine import FALLBACK_TEXT, LLMEngine
from app.llm.prompts import build_initial_user_prompt, build_system_prompt
from app.models import Script, Campaign, CampaignContact, Conversation, Contact, Message

logger = logging.getLogger(__name__)

settings = get_settings()
_bot: Bot | None = None
dp = Dispatcher(storage=MemoryStorage())
router = Router()

TONE_OPTIONS = ["Деловой", "Дружелюбный", "Агрессивный"]
TONE_MAP = {
    "Деловой": "professional",
    "Дружелюбный": "friendly",
    "Агрессивный": "aggressive",
}


COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="help", description="Помощь и схема"),
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
            [KeyboardButton(text="Scripts"), KeyboardButton(text="Campaigns")],
            [KeyboardButton(text="Upload"), KeyboardButton(text="Analytics")],
            [KeyboardButton(text="Hot Leads"), KeyboardButton(text="Help")],
        ],
        resize_keyboard=True,
    )


@dp.startup()
async def on_startup(bot: Bot):
    await bot.set_my_commands(COMMANDS)


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.admin_bot_token)
    return _bot


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
            f"Campaigns: {campaign_count}\n"
            f"Goal: {s.goal}\n"
            f"Max messages: {s.max_messages} | Tone: {s.tone}"
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
            f"Script: {script_name}\n"
            f"Status: {c.status}\n"
            f"Contacts: {c.processed_contacts}/{c.total_contacts}\n"
            f"Replied: {c.replied_count} | Qualified: {c.qualified_count} | Meetings: {c.meeting_booked_count}"
        )
    return "\n\n".join(lines)


def _build_campaign_buttons(campaign) -> list:
    """Return action buttons appropriate for the campaign status."""
    status = campaign.status
    name = campaign.name[:18]

    if status == "draft":
        return [
            types.InlineKeyboardButton(text=f"▶️ {name}", callback_data=f"camp_start:{campaign.id}"),
            types.InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}"),
        ]
    elif status == "running":
        return [
            types.InlineKeyboardButton(text=f"⏸ {name}", callback_data=f"camp_pause:{campaign.id}"),
            types.InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}"),
        ]
    elif status == "paused":
        return [
            types.InlineKeyboardButton(text=f"▶️ {name}", callback_data=f"camp_resume:{campaign.id}"),
            types.InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}"),
        ]
    else:
        return [types.InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"camp_delete:{campaign.id}")]


def _format_hotleads(rows: List) -> str:
    lines = []
    for idx, (conv, contact) in enumerate(rows, 1):
        name = contact.telegram_username or contact.phone or str(contact.id)[:8]
        state_emoji = "🔥" if conv.current_state == "hot" else "📅"
        lines.append(
            f"{idx}. {state_emoji} <b>{name}</b>\n"
            f"State: {conv.current_state}\n"
            f"Sentiment: {conv.sentiment or 'N/A'}"
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
        f"Hot leads: {hot}\n"
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
        "👋 Welcome to AI Sales Manager Admin Bot!\n\n"
        "Выберите раздел в меню ниже или используйте команды.\n\n"
        "/scripts — список скриптов\n"
        "/campaigns — список кампаний\n"
        "/analytics — аналитика\n"
        "/hotleads — горячие лиды\n"
        "/upload — импорт контактов\n"
        "/newscript — создать скрипт\n"
        "/startcampaign — запустить кампанию\n"
        "/discover — поиск лидов\n"
        "/help — помощь"
    )
    await message.answer(welcome, reply_markup=_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "Структура проекта:\n\n"
        "Script (сценарий общения)\n"
        "  ↓\n"
        "Campaign (рассылка по списку контактов)\n"
        "  ↓\n"
        "Contact (человек) → Conversation (диалог)\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/help — помощь\n"
        "/scripts — список скриптов\n"
        "/campaigns — список кампаний\n"
        "/upload — импорт контактов\n"
        "/analytics — аналитика\n"
        "/hotleads — горячие лиды\n"
        "/newscript — создать скрипт\n"
        "/startcampaign — запустить кампанию\n"
        "/discover — поиск лидов\n"
        "/conversations — история по contact_id"
    )
    await message.answer(text, reply_markup=_main_menu_keyboard())


@router.message(Command("scripts"))
async def cmd_scripts(message: types.Message):
    async with AsyncSessionLocal() as session:
        campaign_count = (
            select(func.count(Campaign.id))
            .where(Campaign.script_id == Script.id)
            .scalar_subquery()
        )
        result = await session.execute(
            select(Script, campaign_count).order_by(Script.created_at.desc()).limit(20)
        )
        scripts = result.all()

    if not scripts:
        await message.answer("No scripts found.")
        return

    text = _format_scripts(scripts)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_scripts")]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "refresh_scripts")
async def refresh_scripts(callback: types.CallbackQuery):
    await cmd_scripts(callback.message)
    await callback.answer()


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
        text = "No campaigns found."
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
            asyncio.create_task(_process_campaign_safely(campaign.id, process_campaigns))
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
            select(func.count(Conversation.id)).where(Conversation.current_state == "hot")
        )
        meetings = await session.scalar(
            select(func.count(Conversation.id)).where(Conversation.current_state == "meeting_booked")
        )
        rejected = await session.scalar(
            select(func.count(Message.id))
            .where(Message.direction == "outbound")
            .where(Message.llm_model == "fallback")
        )
        avg_length = await session.scalar(
            select(func.coalesce(func.avg(func.length(Message.content)), 0))
            .where(Message.direction == "outbound")
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
            [types.InlineKeyboardButton(text="📋 Экспорт в CSV", callback_data="export_analytics")],
            [types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_analytics")],
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
    writer.writerow([
        "contact_id", "username", "first_name", "last_name", "company",
        "position", "campaign", "campaign_status", "contact_status",
    ])
    for contact, campaign, cc in rows:
        writer.writerow([
            str(contact.id),
            contact.telegram_username,
            contact.first_name,
            contact.last_name,
            contact.company_name,
            contact.position,
            campaign.name,
            campaign.status,
            cc.status,
        ])

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
        await message.answer("No hot leads or meetings booked.")
        return

    text = _format_hotleads(rows)
    kb_rows = []
    for conv, contact in rows:
        kb_rows.append(
            [
                types.InlineKeyboardButton(text="✅ Qualified", callback_data=f"qualify:{conv.id}"),
                types.InlineKeyboardButton(text="❌ Rejected", callback_data=f"reject:{conv.id}"),
                types.InlineKeyboardButton(text="📜 История диалога", callback_data=f"history:{conv.id}"),
            ]
        )
        kb_rows.append(
            [types.InlineKeyboardButton(text="📋 Диалог", callback_data=f"dialog:{conv.id}")]
        )
    kb_rows.append([types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_hotleads")])
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
        result = await session.execute(select(Conversation).where(Conversation.id == conv_id))
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
        result = await session.execute(select(Conversation).where(Conversation.id == conv_id))
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
        await message.answer("Usage: /conversations <contact_id>")
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
    await message.answer("Введите роль (role_prompt), например:\n'Ты менеджер по продажам MedTech решений.'")


@router.message(ScriptCreateFSM.role_prompt)
async def process_script_role(message: types.Message, state: FSMContext):
    await state.update_data(role_prompt=message.text)
    await state.set_state(ScriptCreateFSM.target_audience)
    await message.answer("Введите целевую аудиторию (или отправьте '-' чтобы пропустить):")


@router.message(ScriptCreateFSM.target_audience)
async def process_script_audience(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(target_audience=None if text == "-" else text)
    await state.set_state(ScriptCreateFSM.goal)
    await message.answer("Введите цель диалога (goal), например:\n'Назначить демонстрацию продукта'")


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
                types.InlineKeyboardButton(text="Hook (мягкий контакт)", callback_data="fmg:hook"),
                types.InlineKeyboardButton(text="Qualification (вопрос)", callback_data="fmg:qualification"),
            ],
            [
                types.InlineKeyboardButton(text="Value (ценность)", callback_data="fmg:value"),
                types.InlineKeyboardButton(text="Call (сразу созвон)", callback_data="fmg:cta"),
            ],
        ]
    )
    await callback.message.answer("Выберите цель первого сообщения:", reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("fmg:"))
async def process_script_first_message_goal(callback: types.CallbackQuery, state: FSMContext):
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
            [types.InlineKeyboardButton(text="Запрещены", callback_data="emoji:forbidden")],
            [types.InlineKeyboardButton(text="Редко", callback_data="emoji:rare")],
            [types.InlineKeyboardButton(text="Разрешены", callback_data="emoji:allowed")],
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
async def process_script_max_first_message_length(message: types.Message, state: FSMContext):
    try:
        val = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    await state.update_data(max_first_message_length=val)
    await state.set_state(ScriptCreateFSM.max_messages)
    await message.answer("Введите максимальное количество сообщений на контакт (например, 2):")


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
            [types.InlineKeyboardButton(text="✅ Подтвердить 09:00-18:00", callback_data="workhours:default")],
            [types.InlineKeyboardButton(text="📝 Указать вручную", callback_data="workhours:manual")],
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
    await callback.message.answer("Введите начало рабочих часов (HH:MM, например 09:00):")
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
        await message.answer("❌ Неверный формат. Введите HH:MM-HH:MM или два отдельных значения.")


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
    tz = message.text.strip() or "Europe/Moscow"
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
            [types.InlineKeyboardButton(text="✅ Создать", callback_data="script:create")],
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data="script:cancel")],
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
    await callback.message.answer(f"Скрипт <b>{script.name}</b> создан.", parse_mode="HTML")


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
        "Пример CSV:\n"
        "first_name,last_name,company_name,position,city,industry,telegram_user_id,phone\n"
        "Иван,Иванов,ООО Ромашка,Директор,Москва,IT,123456789,+79990000000"
    )


@router.message(CSVImportFSM.waiting_file)
async def process_upload_file(message: types.Message, state: FSMContext):
    if not message.document:
        await message.answer("❌ Пожалуйста, отправьте файл.")
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
            f"{r.get('company_name') or ''}, {r.get('position') or ''} (@{r.get('telegram_username') or '-'}, {r.get('phone') or '-'})"
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
                types.InlineKeyboardButton(text="✅ Создать кампанию", callback_data="csv:create_campaign"),
                types.InlineKeyboardButton(text="❌ Отмена", callback_data="csv:cancel"),
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
    data = await state.get_data()
    records = data.get("records", [])
    if not records:
        await callback.answer("❌ Нет контактов")
        await state.clear()
        return

    await state.set_state(CampaignCreateFSM.select_script)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Script).where(Script.is_active == True).order_by(Script.created_at.desc()).limit(20)
        )
        scripts = result.scalars().all()

    if not scripts:
        await callback.message.answer("❌ Нет активных скриптов. Сначала создайте скрипт через /newscript")
        await state.clear()
        return

    kb_rows = [
        [types.InlineKeyboardButton(text=s.name, callback_data=f"campaign_script:{s.id}")]
        for s in scripts
    ]
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await callback.message.answer("Выберите скрипт для кампании:", reply_markup=kb)
    await callback.answer()


# ---------------------------------------------------------------------------
# FSM: Campaign creation from import / discover
# ---------------------------------------------------------------------------

def _preview_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Запустить", callback_data="preview:launch"),
                types.InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="preview:regenerate"),
            ],
            [types.InlineKeyboardButton(text="✏️ Изменить скрипт", callback_data="preview:change_script")],
        ]
    )


async def _generate_preview_message(script: Script, record: dict) -> str:
    stage = get_first_stage(script)
    contact = SimpleNamespace(**record)
    messages = [
        {"role": "system", "content": build_system_prompt(script, conversation_stage=stage)},
        {"role": "user", "content": build_initial_user_prompt(script, contact, conversation_stage=stage)},
    ]
    try:
        engine = LLMEngine()
        result = await engine.generate_response_with_guardrails(
            messages,
            last_messages=[],
            max_retries=2,
            max_tokens=get_max_length_for_stage(script, stage),
        )
        return result.get("text", FALLBACK_TEXT)
    except Exception:
        logger.exception("Failed to generate campaign preview")
        return FALLBACK_TEXT


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
    await callback.message.answer(text, reply_markup=_preview_keyboard())
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
    await callback.message.edit_text(text, reply_markup=_preview_keyboard())
    await callback.answer("🔄 Обновлено")


@router.callback_query(lambda c: c.data == "preview:change_script")
async def handle_preview_change_script(callback: types.CallbackQuery, state: FSMContext):
    await start_campaign_from_csv(callback, state)


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
                types.InlineKeyboardButton(text="▶️ Запустить", callback_data="campaign:start_now"),
                types.InlineKeyboardButton(text="⏸ Позже", callback_data="campaign:start_later"),
            ],
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data="campaign:cancel")],
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
    asyncio.create_task(_process_campaign_safely(campaign.id, process_campaigns))


async def _process_campaign_safely(campaign_id, process_campaigns_fn):
    """Run process_campaigns in a fresh session and log any errors."""
    try:
        async with AsyncSessionLocal() as session:
            await process_campaigns_fn(session)
    except Exception:
        logger.exception("Background process_campaigns failed for campaign %s", campaign_id)


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
                types.InlineKeyboardButton(text="🔍 Telegram Search", callback_data="discover:telegram_search"),
                types.InlineKeyboardButton(text="📢 Мои каналы", callback_data="discover:channel_parse"),
                types.InlineKeyboardButton(text="🌐 Внешняя база", callback_data="discover:external_api"),
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
    preview_text = "\n".join(preview_lines) if preview_lines else "(нет данных для предпросмотра)"

    text = (
        f"Найдено {len(results)} контактов. Валидно {valid_count}.\n\n"
        f"Первые {min(len(results), 5)}:\n{preview_text}\n\n"
        f"Добавить в базу?"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Добавить и создать кампанию", callback_data="discover_confirm:add"),
                types.InlineKeyboardButton(text="📋 Предпросмотр", callback_data="discover_confirm:preview"),
            ],
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data="discover_confirm:cancel")],
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
            select(Campaign).where(Campaign.status == "draft").order_by(Campaign.created_at.desc()).limit(20)
        )
        campaigns = result.scalars().all()

    if not campaigns:
        await message.answer("Нет кампаний со статусом draft.")
        return

    await state.set_state(CampaignStartFSM.selecting)
    kb_rows = []
    for c in campaigns:
        kb_rows.append([types.InlineKeyboardButton(text=c.name, callback_data=f"startcamp:{c.id}")])
    kb_rows.append([types.InlineKeyboardButton(text="❌ Отмена", callback_data="startcamp:cancel")])
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
        try:
            await process_campaigns(session)
        except Exception:
            logger.exception("Immediate process_campaigns failed after campaign start")

    await state.clear()
    await callback.answer("✅ Кампания запущена!")
    await callback.message.answer(f"Кампания <b>{campaign.name}</b> запущена.", parse_mode="HTML")


MENU_HANDLERS = {
    "Scripts": cmd_scripts,
    "Campaigns": cmd_campaigns,
    "Upload": cmd_upload,
    "Analytics": cmd_analytics,
    "Hot Leads": cmd_hotleads,
    "Help": cmd_help,
}


@router.message(F.text.in_(set(MENU_HANDLERS.keys())))
async def handle_menu_button(message: types.Message, state: FSMContext):
    handler = MENU_HANDLERS[message.text]
    if message.text == "Upload":
        await handler(message, state)
    else:
        await handler(message)


dp.include_router(router)


async def start_bot():
    if not settings.admin_bot_token:
        logger.warning("ADMIN_BOT_TOKEN is not set, bot will not start.")
        return
    bot = _get_bot()
    await dp.start_polling(bot)


async def stop_bot():
    if _bot is not None:
        await _bot.session.close()
