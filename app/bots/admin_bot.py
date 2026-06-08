import logging
from typing import List

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from sqlalchemy import select, func

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import Script, Campaign, Conversation, Contact

logger = logging.getLogger(__name__)

settings = get_settings()
_bot: Bot | None = None
dp = Dispatcher()
router = Router()


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.admin_bot_token)
    return _bot


def _format_scripts(scripts: List[Script]) -> str:
    lines = []
    for s in scripts:
        status = "✅" if s.is_active else "❌"
        lines.append(
            f"{status} <b>{s.name}</b>\n"
            f"Goal: {s.goal}\n"
            f"Max messages: {s.max_messages} | Tone: {s.tone}"
        )
    return "\n\n".join(lines)


def _format_campaigns(campaigns: List[Campaign]) -> str:
    lines = []
    for c in campaigns:
        lines.append(
            f"📢 <b>{c.name}</b>\n"
            f"Status: {c.status}\n"
            f"Contacts: {c.processed_contacts}/{c.total_contacts}\n"
            f"Replied: {c.replied_count} | Qualified: {c.qualified_count} | Meetings: {c.meeting_booked_count}"
        )
    return "\n\n".join(lines)


def _format_hotleads(rows: List) -> str:
    lines = []
    for conv, contact in rows:
        name = contact.telegram_username or contact.phone or str(contact.id)[:8]
        state_emoji = "🔥" if conv.current_state == "hot" else "📅"
        lines.append(
            f"{state_emoji} <b>{name}</b>\n"
            f"State: {conv.current_state}\n"
            f"Sentiment: {conv.sentiment or 'N/A'}"
        )
    return "\n\n".join(lines)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome = (
        "👋 Welcome to AI Sales Manager Admin Bot!\n\n"
        "Available commands:\n"
        "/scripts — list all scripts\n"
        "/campaigns — list campaigns with status\n"
        "/analytics — show dashboard metrics\n"
        "/hotleads — list hot leads & meetings booked"
    )
    await message.answer(welcome)


@router.message(Command("scripts"))
async def cmd_scripts(message: types.Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Script).order_by(Script.created_at.desc()).limit(20)
        )
        scripts = result.scalars().all()

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


@router.message(Command("campaigns"))
async def cmd_campaigns(message: types.Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Campaign).order_by(Campaign.created_at.desc()).limit(20)
        )
        campaigns = result.scalars().all()

    if not campaigns:
        await message.answer("No campaigns found.")
        return

    text = _format_campaigns(campaigns)
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_campaigns")]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "refresh_campaigns")
async def refresh_campaigns(callback: types.CallbackQuery):
    await cmd_campaigns(callback.message)
    await callback.answer()


@router.message(Command("analytics"))
async def cmd_analytics(message: types.Message):
    async with AsyncSessionLocal() as session:
        total_scripts = await session.scalar(select(func.count(Script.id)))
        total_campaigns = await session.scalar(select(func.count(Campaign.id)))
        total_conversations = await session.scalar(select(func.count(Conversation.id)))
        hot_conversations = await session.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.current_state.in_(["hot", "meeting_booked"])
            )
        )

    text = (
        "📊 Dashboard Metrics\n\n"
        f"Scripts: {total_scripts}\n"
        f"Campaigns: {total_campaigns}\n"
        f"Conversations: {total_conversations}\n"
        f"Hot leads / Meetings: {hot_conversations}"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_analytics")]
        ]
    )
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data == "refresh_analytics")
async def refresh_analytics(callback: types.CallbackQuery):
    await cmd_analytics(callback.message)
    await callback.answer()


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
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_hotleads")]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "refresh_hotleads")
async def refresh_hotleads(callback: types.CallbackQuery):
    await cmd_hotleads(callback.message)
    await callback.answer()


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
