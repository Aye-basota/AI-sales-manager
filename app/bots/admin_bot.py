import logging
from datetime import datetime, time as dt_time, timezone
from io import BytesIO
from typing import List
from uuid import UUID

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select, func

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import Script, Campaign, Conversation, Contact, Message

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
    max_messages = State()
    follow_up_delay_hours = State()
    working_hours = State()
    timezone = State()
    confirm = State()


class CSVImportFSM(StatesGroup):
    waiting_file = State()
    preview = State()


class CampaignCreateFSM(StatesGroup):
    select_script = State()
    name = State()
    confirm = State()


class CampaignStartFSM(StatesGroup):
    selecting = State()


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

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
) -> str:
    reply_rate = (replied / sent * 100) if sent else 0
    return (
        "📊 Сводка\n\n"
        f"Всего контактов: {total_contacts}\n"
        f"Отправлено: {sent}\n"
        f"Ответили: {replied} ({reply_rate:.1f}%)\n"
        f"Hot leads: {hot}\n"
        f"Встречи: {meetings}"
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome = (
        "👋 Welcome to AI Sales Manager Admin Bot!\n\n"
        "Available commands:\n"
        "/scripts — list all scripts\n"
        "/campaigns — list campaigns with status\n"
        "/analytics — show dashboard metrics\n"
        "/hotleads — list hot leads & meetings booked\n"
        "/newscript — create a new script step-by-step\n"
        "/upload — import contacts from CSV or Excel\n"
        "/discover — find leads via Telegram or external sources\n"
        "/startcampaign — start a draft campaign"
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
    kb_rows = []
    for c in campaigns:
        kb_rows.append(
            [
                types.InlineKeyboardButton(text=f"⏸ {c.name[:20]}", callback_data=f"camp_pause:{c.id}"),
                types.InlineKeyboardButton(text=f"▶️ {c.name[:20]}", callback_data=f"camp_resume:{c.id}"),
                types.InlineKeyboardButton(text=f"🛑 {c.name[:20]}", callback_data=f"camp_stop:{c.id}"),
            ]
        )
    kb_rows.append([types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_campaigns")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "refresh_campaigns")
async def refresh_campaigns(callback: types.CallbackQuery):
    await cmd_campaigns(callback.message)
    await callback.answer()


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
    await cmd_campaigns(callback.message)


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
    await cmd_campaigns(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("camp_stop:"))
async def handle_camp_stop(callback: types.CallbackQuery):
    camp_id_str = callback.data.split(":", 1)[1]
    try:
        camp_id = UUID(camp_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.id == camp_id))
        campaign = result.scalar_one_or_none()
        if campaign and campaign.status in ("running", "paused"):
            campaign.status = "closed"
            await session.commit()
            await callback.answer("🛑 Остановлено")
        else:
            await callback.answer("❌ Нельзя остановить")
    await cmd_campaigns(callback.message)


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

    text = _format_analytics(total_contacts or 0, sent or 0, replied or 0, hot or 0, meetings or 0)
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
                types.InlineKeyboardButton(text="📋 Диалог", callback_data=f"dialog:{conv.id}"),
            ]
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
    await state.set_state(ScriptCreateFSM.max_messages)
    await callback.message.answer("Введите максимальное количество сообщений на контакт (например, 2):")
    await callback.answer()


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
        f"Рабочие часы по умолчанию: 09:00 - 18:00.\nЧто выберете?",
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
        else:
            # Expect single start time for now, then prompt for end
            start_str = message.text.strip()
            await state.update_data(_start_tmp=start_str)
            await message.answer("Введите конец рабочих часов (HH:MM, например 18:00):")
            return

        h1, m1 = map(int, start_str.split(":"))
        h2, m2 = map(int, end_str.split(":"))
        await state.update_data(working_hours_start=dt_time(h1, m1))
        await state.update_data(working_hours_end=dt_time(h2, m2))
        await state.set_state(ScriptCreateFSM.timezone)
        await message.answer("Введите timezone (по умолчанию Europe/Moscow):")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите HH:MM-HH:MM или два отдельных значения.")


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
        "Ожидаемые колонки: first_name, last_name, company_name, position, city, industry, telegram_username, phone"
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

@router.callback_query(lambda c: c.data and c.data.startswith("campaign_script:"))
async def process_campaign_script(callback: types.CallbackQuery, state: FSMContext):
    script_id_str = callback.data.split(":", 1)[1]
    try:
        script_id = UUID(script_id_str)
    except ValueError:
        await callback.answer("❌ Неверный ID скрипта")
        await state.clear()
        return

    await state.update_data(script_id=script_id)
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
            from app.models.campaign import CampaignContact
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
            from app.models.campaign import CampaignContact
            cc = CampaignContact(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status="pending",
                message_count=0,
            )
            session.add(cc)

        campaign.total_contacts = len(contacts)
        await session.commit()

        from app.core.scheduler import process_campaigns
        try:
            await process_campaigns(session)
        except Exception:
            logger.exception("Immediate process_campaigns failed after campaign start")

    await state.clear()
    await callback.answer("✅ Кампания запущена!")
    await callback.message.answer(
        f"Кампания <b>{campaign.name}</b> запущена с {campaign.total_contacts} контактами.",
        parse_mode="HTML",
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
            pass

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
