"""Inbound message listener using Pyrogram."""

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    # Pyrogram's sync module calls asyncio.get_event_loop() at import time.
    # When uvloop is the active policy and no loop exists yet, this raises.
    # Create a temporary loop so the import succeeds; uvicorn will replace it later.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        _tmp_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_tmp_loop)

    from pyrogram.types import Message

    _PYROGRAM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYROGRAM_AVAILABLE = False

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.telegram_account import TelegramAccount
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.campaign import Campaign, CampaignContact
from app.models.script import Script
from app.bots.seller_client import SellerClient
from app.llm.engine import LLMEngine
from app.llm.intent_classifier import classify_intent
from app.llm.prompts import build_system_prompt, build_reply_user_prompt
from app.core.humanizer import (
    calculate_typing_delay,
    calculate_thinking_delay,
    split_message_into_chunks,
)
from app.core.funnel import next_stage
from app.core.state_machine import is_terminal, transition
from app.services.notification_service import NotificationService
from app.services.conversation_service import (
    get_conversation_context,
    add_message,
    extract_facts_from_message,
    update_lead_facts,
)

logger = logging.getLogger(__name__)

_inbound_clients: dict[str, SellerClient] = {}

FALLBACK_TEXT = (
    "Извините, я не до конца понял контекст. Сформулирую проще: мы помогаем "
    "аккуратнее начинать диалоги с потенциальными клиентами без лишней ручной рутины."
)
PUNCTUATION_ONLY_CHARS = {"?", "!", ".", " "}
BOT_CHECK_PATTERNS = (
    r"(?<![0-9a-zа-яё])бот(?![0-9a-zа-яё])",
    r"(?<![0-9a-zа-яё])ии(?![0-9a-zа-яё])",
    r"(?<![0-9a-zа-яё])ai(?![0-9a-zа-яё])",
    r"нейросет",
    r"автомат",
)
DELIVERY_RISK_PATTERNS = (
    r"спам",
    r"заблок",
    r"забан",
    r"(?<![0-9a-zа-яё])бан(?![0-9a-zа-яё])",
    r"лимит",
    r"telegram.*руг",
    r"руг.*telegram",
    r"telegram.*огранич",
    r"огранич.*telegram",
)
SECURITY_PATTERNS = (
    r"безопасн",
    r"доступ",
    r"персональн.*данн",
    r"данн",
)
WRONG_PERSON_PATTERNS = (
    r"не\s+ко\s+мне",
    r"не\s+занимаюсь",
    r"не\s+принимаю\s+.*решени",
)
PAUSE_PATTERNS = (
    r"не\s+до\s+этого",
    r"напишите\s+через",
    r"вернемся\s+к\s+этому",
    r"верн[её]мся\s+позже",
    r"давайте\s+(?:позже|потом)",
    r"может\s+потом",
    r"через\s+пару\s+месяц",
)
PRICING_PATTERNS = (
    r"\bцен(?:а|у|ы|е|ой)?\b",
    r"ценник",
    r"прайс",
    r"цифр",
    r"стоим",
    r"стоит",
    r"сколько.*стоит",
    r"дорого",
    r"бюджет",
)
INTEGRATION_PATTERNS = (
    r"интеграц",
    r"amocrm",
    r"амоcrm",
    r"bitrix",
    r"битрикс",
    r"\bcrm\b.*(?:связ|интеграц)",
    r"(?:связ|интеграц).*\bcrm\b",
)
CASE_PATTERNS = (
    r"кейс",
    r"пример",
    r"результат",
)
CONTACT_SOURCE_PATTERNS = (
    r"откуда\s+.*контакт",
    r"где\s+.*контакт",
    r"кто\s+вы",
    r"вы\s+кто",
)
COMPETITOR_PATTERNS = (
    r"обычн.*рассыл",
    r"чем\s+.*отлич",
    r"массов.*отправ",
)
SHORT_POSITIVE_PATTERNS = (
    r"^\s*(?:да|ок|ок[,.]?\s*интересно|интересно|да[,.]?\s*интересно|расскажите|давайте)\s*[.!?]*\s*$",
)
MATERIALS_REQUEST_PATTERNS = (
    r"пришл",
    r"материал",
    r"пример",
    r"фото",
    r"картинк",
    r"каталог",
    r"презентац",
    r"коротко.*что\s+у\s+вас",
    r"что\s+у\s+вас\s+есть",
)
CREATIVE_TERRITORY_PATTERNS = (
    r"дизайн",
    r"концепц",
    r"макет",
    r"брендбук",
    r"логотип",
    r"визуал",
    r"цвет",
    r"шрифт",
    r"стиль",
    r"атмосфер",
    r"аудитор",
    r"ценност",
    r"вариант",
)
CONTEXT_CONFUSION_PATTERNS = (
    r"что\s+ещ[её]\s+за\s+сценар",
    r"о\s+ч[её]м\s+вы",
    r"вы\s+о\s+ч[её]м",
    r"не\s+понимаю",
)
ENGLISH_REQUEST_PATTERNS = (
    r"\benglish\b",
    r"explain\s+in\s+english",
)


def _matches_any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _event_from_intent(intent: str) -> str:
    return {
        "meeting_intent": "meeting_intent",
        "positive": "positive_reply",
        "negative": "negative_reply",
        "objection": "objection",
        "question": "informational",
        "informational": "informational",
    }.get(intent, "positive_reply")


def _sentiment_from_intent(intent: str) -> str:
    if intent in ("positive", "meeting_intent"):
        return "positive"
    if intent == "negative":
        return "negative"
    return "neutral"


def _terminal_response(intent: str) -> str:
    if intent == "negative":
        return "Понял, извините за беспокойство. Больше не буду писать."
    if intent == "meeting_intent":
        return "Отлично, договорились. Спасибо, дальше продолжим уже по созвону."
    return ""


def _script_offer_context(script: Script | None) -> str:
    if not script:
        return "помогаем решить эту задачу аккуратно и без лишней ручной рутины"
    default = "помогаем B2B-командам аккуратно начинать первые диалоги без лишней ручной рутины"
    for attr in ("role_prompt", "goal", "target_audience"):
        value = getattr(script, attr, None)
        if value:
            text = " ".join(str(value).split())
            lowered = text.lower()
            if attr == "role_prompt" and any(
                marker in lowered
                for marker in (
                    "ты ",
                    "пиши ",
                    "не называй",
                    "бот",
                    "ии",
                    "sales manager",
                )
            ):
                continue
            if any(marker in lowered for marker in ("созвон", "встреч", "договориться")):
                continue
            if attr == "target_audience" and "b2b founders" in lowered:
                return default
            if len(text) > 180:
                text = text[:179].rstrip() + "…"
            return text
    return default


def _polish_inbound_response(text: str) -> str:
    """Reduce robotic reply patterns before sending a message to the lead."""
    cleaned = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    if not cleaned:
        return cleaned

    cleaned = re.sub(
        r"(?i)понимаю,\s*а\s+как\s+сейчас\s+решаете\s+эту\s+задачу\??",
        "Понимаю, спасибо за контекст.",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)как\s+сейчас\s+решаете\s+эту\s+задачу\??",
        "как это устроено сейчас?",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)\bкак\s+(?:вы\s+)?(?:сейчас\s+)?решаете\b[^?]*\?",
        "как это устроено сейчас?",
        cleaned,
    )
    cleaned = re.sub(r"(?i)\bв\s+вашем\s+стеке\b", "у вас", cleaned)
    cleaned = re.sub(r"(?i)\bAI\s+Sales\s+Manager\b", "наш инструмент", cleaned)
    cleaned = re.sub(r"(?i)\bleads\b", "лидами", cleaned)
    cleaned = re.sub(r"(?i)Neural\s+лидом", "Neural Lead", cleaned)
    cleaned = re.sub(
        r"(?i)^\s*(?:понял|понимаю),?\s+что\s+у\s+вас\s+",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\s+—\s+", ", ", cleaned)
    cleaned = re.sub(r"(?i)\bкоротко:\s*", "Коротко, ", cleaned)
    cleaned = re.sub(
        r"(?i)\b(?:присылаю|прикрепляю|отправляю)\b",
        "Могу описать словами",
        cleaned,
    )
    cleaned = re.sub(r"(?i)\bкруто,\s*сразу\s+понятно,?\s*", "", cleaned)
    cleaned = re.sub(r"(?i)\bсразу\s+понятно,?\s*", "предварительно понятно, ", cleaned)
    cleaned = re.sub(r"(?i)\bнедавно\s+делали\b", "если есть похожие вводные, обычно обсуждаем", cleaned)
    cleaned = re.sub(
        r"(?i)\bвот\s+(?:два|три|несколько)\s+вариант\w*:?\.?",
        "Конкретные варианты лучше не придумывать в переписке без вводных.",
        cleaned,
    )

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    if len(paragraphs) > 2:
        cleaned = " ".join(paragraphs)

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    kept: list[str] = []
    question_seen = False
    for sentence in sentences:
        if not sentence:
            continue
        if "?" in sentence:
            if question_seen:
                continue
            question_seen = True
            kept.append(sentence)
            break
        kept.append(sentence)

    return " ".join(kept).strip()


def _build_inbound_fallback_text(lead_text: str, script: Script) -> str:
    lower = lead_text.lower()
    offer = _script_offer_context(script)

    if _matches_any(BOT_CHECK_PATTERNS, lower):
        return (
            "Понимаю вопрос. Пишу из рабочего Telegram; если сообщение неактуально, "
            "спокойно остановлюсь.\n\n"
            "Могу коротко объяснить, почему обратился?"
        )

    if _matches_any(DELIVERY_RISK_PATTERNS, lower):
        return (
            "Понимаю риск блокировки — это правда важный момент.\n\n"
            "Мы не предлагаем массово слать одинаковые сообщения: сначала проверяем базу, "
            "лимиты, паузы и реакцию на малом объеме. Если появляется риск, отправку лучше "
            "остановить и разобрать причину, а не продолжать давить."
        )

    if _matches_any(SECURITY_PATTERNS, lower):
        return (
            "Про доступы и данные лучше говорить аккуратно: без вашей схемы не буду "
            "обещать лишнего. Обычно сначала фиксируют, какие данные нужны, кто их видит "
            "и как быстро можно отозвать доступ, а уже потом включают отправку."
        )

    if _matches_any(WRONG_PERSON_PATTERNS, lower):
        return (
            "Понял, извините, что написал не по адресу. Не буду отвлекать, "
            "спасибо, что ответили."
        )

    if _matches_any(PAUSE_PATTERNS, lower):
        return "Понял, не отвлекаю. Тогда вернусь позже, хорошего дня."

    if _matches_any(CONTEXT_CONFUSION_PATTERNS, lower):
        return (
            f"Извините, сбился формулировкой. Речь именно про это: {offer}. "
            "Без внутренних терминов: могу коротко ответить по условиям, срокам или следующему шагу."
        )

    if _matches_any(PRICING_PATTERNS, lower):
        offer_lower = offer.lower()
        if any(marker in offer_lower for marker in ("стакан", "cup", "кофе")):
            return (
                "По цене не буду называть точную цифру без вводных: она зависит от тиража, "
                "материала, объема стакана, печати и регулярности поставок. "
                "Если дадите примерный недельный или месячный объем, можно посчитать ближе к делу."
            )
        return (
            "По цене не буду называть цифру без вводных: она зависит от объема, формата "
            "работы и требований к качеству. Обычно сначала фиксируют вводные, а потом "
            "уже считают оценку без гадания."
        )

    if _matches_any(INTEGRATION_PATTERNS, lower):
        return (
            "По интеграциям не буду обещать без проверки вашей схемы. Обычно сначала "
            "смотрим, какие данные нужно передавать между CRM и диалогами, а потом уже "
            "понятно, насколько просто это связать."
        )

    if _matches_any(CASE_PATTERNS, lower):
        return (
            f"Не буду выдумывать кейсы или делать вид, что прикрепил файл. По сути: {offer}. "
            "Могу описать словами типовой вариант работы и что обычно нужно уточнить для расчета."
        )

    if _matches_any(CONTACT_SOURCE_PATTERNS, lower):
        return (
            "Я из Neural Lead. Написал по рабочему контакту из открытого контекста; "
            "если неактуально, спокойно остановлюсь."
        )

    if _matches_any(COMPETITOR_PATTERNS, lower):
        return (
            "Отличие не в массовой отправке, а в аккуратном выборе контактов, "
            "персонализации и остановке, если человеку неактуально. Идея в том, "
            "чтобы не давить объемом, а вести первый диалог бережно."
        )

    if _matches_any(MATERIALS_REQUEST_PATTERNS, lower):
        return (
            "Я не могу прикрепить фото, файл или презентацию прямо здесь, поэтому не буду "
            f"делать вид, что отправил материалы. Могу описать словами: {offer}. "
            "Дальше лучше сверить нужный формат, объем и сроки."
        )

    if _matches_any(CREATIVE_TERRITORY_PATTERNS, lower):
        return (
            "Я не знаю вашу концепцию заранее и не буду придумывать дизайн на ходу. "
            "Могу зафиксировать вводные для специалиста: стиль, аудиторию, объемы и сроки. "
            "Если актуально, лучше коротко сверить это на созвоне."
        )

    if _matches_any(SHORT_POSITIVE_PATTERNS, lower):
        return (
            f"Отлично. Коротко по сути: {offer}. Обычно начинаем с небольшого объема, "
            "смотрим реакцию людей и быстро убираем формулировки, которые звучат давяще."
        )

    if _matches_any(ENGLISH_REQUEST_PATTERNS, lower):
        return (
            "In short: it helps teams start careful first conversations with potential "
            "B2B clients in Telegram, without turning outreach into mass spam."
        )

    if lead_text.strip() and set(lead_text.strip()) <= PUNCTUATION_ONLY_CHARS:
        return (
            "Понял, похоже написал не в самый удобный момент.\n\n"
            "Скажите, актуально ли вам сейчас улучшать обработку лидов, или лучше не беспокоить?"
        )

    return (
        "Похоже, я не до конца точно понял вопрос. Сформулирую проще: "
        f"{offer}. Если актуально, могу коротко разложить следующий шаг."
    )


def _needs_deterministic_fallback(lead_text: str) -> bool:
    """Use hand-written replies for high-risk lead messages."""
    lower = lead_text.lower()
    if lead_text.strip() and set(lead_text.strip()) <= PUNCTUATION_ONLY_CHARS:
        return True
    return _matches_any(
        BOT_CHECK_PATTERNS
        + DELIVERY_RISK_PATTERNS
        + SECURITY_PATTERNS
        + WRONG_PERSON_PATTERNS
        + PAUSE_PATTERNS
        + PRICING_PATTERNS
        + INTEGRATION_PATTERNS
        + CASE_PATTERNS
        + CONTACT_SOURCE_PATTERNS
        + COMPETITOR_PATTERNS
        + MATERIALS_REQUEST_PATTERNS
        + CREATIVE_TERRITORY_PATTERNS
        + CONTEXT_CONFUSION_PATTERNS
        + SHORT_POSITIVE_PATTERNS
        + ENGLISH_REQUEST_PATTERNS,
        lower,
    )


async def start_inbound_listeners(db_session: AsyncSession | None = None) -> None:
    """Load ready/active accounts and start Pyrogram inbound listeners."""
    if not _PYROGRAM_AVAILABLE:
        logger.warning("Pyrogram not available, inbound listeners not started")
        return

    if db_session is None:
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(TelegramAccount).where(
                    TelegramAccount.status.in_(["ready", "active"])
                )
            )
            accounts = result.scalars().all()
    else:
        result = await db_session.execute(
            select(TelegramAccount).where(
                TelegramAccount.status.in_(["ready", "active"])
            )
        )
        accounts = result.scalars().all()

    settings = get_settings()

    for account in accounts:
        if not account.session_string:
            logger.debug("Account %s has no session string, skipping", account.id)
            continue

        client = SellerClient(
            account_id=str(account.id),
            session_string=account.session_string,
            proxy_url=account.proxy_url,
            api_id=settings.telegram_api_id or None,
            api_hash=settings.telegram_api_hash or None,
            no_updates=False,
        )

        try:
            await client.start()
        except Exception as exc:
            logger.warning("Failed to start client for account %s: %s", account.id, exc)
            continue

        if client._client is None:
            logger.warning("Pyrogram client not initialised for account %s", account.id)
            continue

        def _make_handler(acc, cl):
            async def _handler(_, message: Message):
                await _handle_inbound_message(acc, cl, message)

            return _handler

        client.on_message(_make_handler(account, client))
        _inbound_clients[str(account.id)] = client
        logger.info("Inbound listener started for account %s", account.id)


async def stop_inbound_listeners() -> None:
    """Stop all active inbound listeners."""
    for account_id, client in list(_inbound_clients.items()):
        try:
            await client.stop()
        except Exception as exc:
            logger.warning("Error stopping inbound listener %s: %s", account_id, exc)
        finally:
            _inbound_clients.pop(account_id, None)
    logger.info("Inbound listeners stopped")


async def _handle_inbound_message(
    account: TelegramAccount,
    client: SellerClient,
    message: Any,
) -> None:
    """Process a single inbound message end-to-end."""
    if not message.from_user:
        return

    telegram_user_id = message.from_user.id
    text = message.text or ""
    if not text:
        logger.debug("Inbound message without text from %s", telegram_user_id)
        return

    async with AsyncSessionLocal() as db:
        try:
            # 1. Find contact
            result = await db.execute(
                select(Contact)
                .where(Contact.telegram_user_id == telegram_user_id)
                .order_by(
                    Contact.updated_at.desc().nullslast(),
                    Contact.created_at.desc().nullslast(),
                )
                .limit(1)
            )
            contact: Contact | None = result.scalars().first()
            if not contact:
                logger.info(
                    "Creating new contact for telegram_user_id %s", telegram_user_id
                )
                contact = Contact(
                    telegram_user_id=telegram_user_id,
                    telegram_username=message.from_user.username or "",
                    first_name=message.from_user.first_name or "",
                    last_name=message.from_user.last_name or "",
                    source="inbound",
                    last_source="inbound",
                    is_valid="unknown",
                )
                db.add(contact)
                await db.commit()
                await db.refresh(contact)

            # 2. Find latest conversation
            result = await db.execute(
                select(Conversation)
                .where(Conversation.contact_id == contact.id)
                .order_by(Conversation.last_message_at.desc().nullslast())
                .limit(1)
            )
            conversation: Conversation | None = result.scalar_one_or_none()

            # 3. Create conversation if missing
            if conversation is None:
                result = await db.execute(
                    select(CampaignContact)
                    .where(CampaignContact.contact_id == contact.id)
                    .order_by(CampaignContact.last_message_at.desc().nullslast())
                )
                cc: CampaignContact | None = result.scalar_one_or_none()
                if not cc:
                    logger.info("Contact %s not in any campaign, skipping", contact.id)
                    return

                result = await db.execute(
                    select(Campaign).where(Campaign.id == cc.campaign_id)
                )
                campaign: Campaign | None = result.scalar_one_or_none()
                if not campaign:
                    logger.info("No campaign found for campaign_contact %s", cc.id)
                    return

                conversation = Conversation(
                    contact_id=contact.id,
                    campaign_id=campaign.id,
                    current_state="cold",
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
            else:
                result = await db.execute(
                    select(Campaign).where(Campaign.id == conversation.campaign_id)
                )
                campaign: Campaign | None = result.scalar_one_or_none()

            if not campaign:
                logger.warning("No campaign for conversation %s", conversation.id)
                return

            # 4. Save inbound message
            await add_message(db, conversation.id, "inbound", text, message_type="text")

            if campaign.status not in ("running",):
                logger.info(
                    "Campaign %s is not running (%s), skipping automated reply",
                    campaign.id,
                    campaign.status,
                )
                return

            # 4.5 Update campaign contact status and analytics only for running campaigns
            cc_result = await db.execute(
                select(CampaignContact)
                .where(CampaignContact.contact_id == contact.id)
                .where(CampaignContact.campaign_id == campaign.id)
            )
            campaign_contact = cc_result.scalar_one_or_none()
            if campaign_contact and campaign_contact.status in (
                "pending",
                "initial_sent",
                "follow_up_sent",
            ):
                campaign_contact.status = "replied"
                campaign_contact.reply_received_at = datetime.now(timezone.utc)
                campaign.replied_count = (campaign.replied_count or 0) + 1
                await db.commit()

            # 5. Mark message as read after a short human-like delay
            user_id = int(contact.telegram_user_id)
            await asyncio.sleep(random.uniform(2.0, 5.0))  # nosec B311
            await client.read_history(user_id)

            # 6. Extract facts from inbound message
            try:
                facts = await extract_facts_from_message(text)
                if facts:
                    await update_lead_facts(db, conversation.id, facts)
            except Exception as exc:
                logger.debug("Failed to extract facts: %s", exc)

            # 7. Load script
            result = await db.execute(
                select(Script).where(Script.id == campaign.script_id)
            )
            script: Script | None = result.scalar_one_or_none()
            if not script:
                logger.warning("No script for campaign %s", campaign.id)
                return

            # 7.5 Load account counters. Terminal acknowledgements below are allowed
            # even when the usual outbound limit is reached, so a refusal or meeting
            # agreement does not leave the lead without a clear final answer.
            settings = get_settings()
            daily_limit = getattr(settings, "daily_message_limit", None) or 50
            account_result = await db.execute(
                select(TelegramAccount).where(TelegramAccount.id == account.id)
            )
            db_account = account_result.scalar_one_or_none() or account
            current_daily = getattr(db_account, "daily_messages_sent", 0) or 0

            # 8. Classify intent
            engine = LLMEngine()
            intent = await classify_intent(text, engine)
            event = _event_from_intent(intent)
            previous_state = conversation.current_state or "cold"
            new_state = transition(previous_state, event)

            # 8.5 Update funnel stage based on intent
            conversation.conversation_stage = next_stage(
                script,
                getattr(conversation, "conversation_stage", None) or "hook",
                intent,
            )
            conversation.current_state = new_state
            conversation.sentiment = _sentiment_from_intent(intent)
            current_facts = dict(conversation.facts_extracted or {})
            current_facts["last_intent"] = intent
            conversation.facts_extracted = current_facts

            if campaign_contact and intent == "meeting_intent":
                campaign_contact.status = "meeting_booked"
                campaign.meeting_booked_count = (campaign.meeting_booked_count or 0) + 1

            if is_terminal(previous_state):
                await db.commit()
                logger.info(
                    "Conversation %s already terminal (%s), skipping automated reply",
                    conversation.id,
                    previous_state,
                )
                return

            terminal_text = _terminal_response(intent)
            if terminal_text:
                response_text = terminal_text
                chunks = split_message_into_chunks(response_text, max_chunks=2)
                base_typing_delay = calculate_typing_delay(response_text)
                thinking_delay = calculate_thinking_delay()
                await client.set_online()
                if thinking_delay > 0:
                    await asyncio.sleep(thinking_delay / 1000.0)
                for chunk in chunks:
                    await client.send_message(
                        user_id=user_id,
                        text=chunk,
                        typing_delay_ms=base_typing_delay,
                    )
                await add_message(
                    db,
                    conversation.id,
                    "outbound",
                    response_text,
                    message_type="text",
                    llm_model="terminal",
                    tokens_used=0,
                    typing_delay_ms=base_typing_delay + thinking_delay,
                    intent_classification=intent,
                )
                db_account.daily_messages_sent = current_daily + len(chunks)
                db_account.last_message_at = datetime.now(timezone.utc)
                await db.commit()

                if intent == "meeting_intent":
                    notif = NotificationService()
                    await notif.send_hot_lead_alert(
                        contact, conversation, last_message_text=text
                    )
                return

            # 8.75 Non-terminal outbound limit guards
            if current_daily >= daily_limit:
                await db.commit()
                logger.warning(
                    "Account %s reached daily limit (%s), skipping inbound reply",
                    account.id,
                    daily_limit,
                )
                return

            # 9. Build context
            context = await get_conversation_context(db, conversation.id, limit=10)

            # 10. Generate response
            conversation_stage = (
                getattr(conversation, "conversation_stage", None) or "hook"
            )
            system_prompt = build_system_prompt(
                script, conversation_stage=conversation_stage
            )

            history = [
                {
                    "role": "agent" if msg.direction == "outbound" else "lead",
                    "content": msg.content,
                }
                for msg in context["messages"]
            ]

            last_agent_msg = ""
            for msg in reversed(history):
                if msg["role"] == "agent":
                    last_agent_msg = msg["content"]
                    break

            user_prompt = build_reply_user_prompt(
                script=script,
                conversation_history=history,
                lead_facts=context["facts"] or {},
                last_agent_message=last_agent_msg,
                lead_message=text,
                conversation_stage=conversation_stage,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Show "online" before generation so the lead sees we are active
            await client.set_online()

            last_outbound = [
                msg.content
                for msg in context["messages"]
                if msg.direction == "outbound"
            ]

            from app.core.funnel import get_max_length_for_stage

            max_length = get_max_length_for_stage(script, conversation_stage)
            max_tokens = int(max_length * 1.5) if max_length else None

            if _needs_deterministic_fallback(text):
                response = {
                    "text": _build_inbound_fallback_text(text, script),
                    "model": "fallback",
                    "tokens_used": 0,
                }
            else:
                try:
                    response = await engine.generate_response_with_guardrails(
                        messages,
                        last_messages=last_outbound,
                        max_retries=1,
                        max_tokens=max_tokens,
                    )
                except Exception as exc:
                    logger.exception("LLM generation failed: %s", exc)
                    response = {"text": "", "model": None, "tokens_used": 0}

            response_text = response.get("text", "")

            # If guardrails blocked even the retry, use fallback text
            if not response_text or response.get("model") == "fallback":
                response_text = _build_inbound_fallback_text(text, script)
            response_text = _polish_inbound_response(response_text)

            # 11. Humanizer delays and chunking
            chunks = split_message_into_chunks(response_text)
            base_typing_delay = calculate_typing_delay(response_text)
            thinking_delay = calculate_thinking_delay()
            chunk_delays = [
                int(base_typing_delay * len(chunk) / max(len(response_text), 1))
                for chunk in chunks
            ]

            from app.core.humanizer import chunk_pause_seconds

            # 12. Send with human-like delays, one chunk at a time
            # "typing" indicator is kept alive during the chunk delays.
            if thinking_delay > 0:
                await asyncio.sleep(thinking_delay / 1000.0)
            sent_chunks = 0
            for idx, chunk in enumerate(chunks):
                if idx > 0:
                    await asyncio.sleep(chunk_pause_seconds())
                await client.send_message(
                    user_id=user_id,
                    text=chunk,
                    typing_delay_ms=chunk_delays[idx],
                )
                sent_chunks += 1

            # 13. Save outbound message (whole text for conversation history)
            await add_message(
                db,
                conversation.id,
                "outbound",
                response_text,
                message_type="text",
                llm_model=response.get("model"),
                tokens_used=response.get("tokens_used"),
                typing_delay_ms=base_typing_delay + thinking_delay,
                intent_classification=intent,
            )

            if sent_chunks:
                db_account.daily_messages_sent = current_daily + sent_chunks
                db_account.last_message_at = datetime.now(timezone.utc)

            await db.commit()

            # 15. Notify if hot lead
            became_hot = new_state in ("hot", "meeting_booked") and previous_state not in (
                "hot",
                "meeting_booked",
            )
            if intent == "meeting_intent" or became_hot:
                notif = NotificationService()
                await notif.send_hot_lead_alert(
                    contact, conversation, last_message_text=text
                )

        except Exception as exc:
            logger.exception(
                "Error handling inbound message from %s: %s", telegram_user_id, exc
            )
