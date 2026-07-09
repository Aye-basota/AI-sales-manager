"""Inbound message listener using Pyrogram."""

import asyncio
import logging
import random
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
from app.core.state_machine import transition
from app.services.notification_service import NotificationService
from app.services.conversation_service import (
    get_conversation_context,
    add_message,
    extract_facts_from_message,
    update_lead_facts,
)

logger = logging.getLogger(__name__)

_inbound_clients: dict[str, SellerClient] = {}

FALLBACK_TEXT = "Извините, не совсем понял. Могу ли я уточнить — вас интересует {goal}?"
PUNCTUATION_ONLY_CHARS = {"?", "!", ".", " "}


def _build_inbound_fallback_text(lead_text: str, script: Script) -> str:
    lower = lead_text.lower()

    if any(word in lower for word in ("бот", "ии", "нейросеть", "автомат", "рассыл")):
        return (
            "Понимаю вопрос. Пишу из рабочего Telegram; если сообщение неактуально, "
            "спокойно остановлюсь.\n\n"
            "Могу коротко объяснить, почему обратился?"
        )

    if any(word in lower for word in ("спам", "заблок", "бан", "лимит")):
        return (
            "Понимаю риск блокировки — это правда важный момент.\n\n"
            "Мы не предлагаем массово слать одинаковые сообщения: сначала проверяем базу, "
            "лимиты, паузы и реакцию на малом объеме. Если актуально, могу коротко рассказать, "
            "как обычно делают безопасный тест."
        )

    if lead_text.strip() and set(lead_text.strip()) <= PUNCTUATION_ONLY_CHARS:
        return (
            "Понял, похоже написал не в самый удобный момент.\n\n"
            "Скажите, актуально ли вам сейчас улучшать обработку лидов, или лучше не беспокоить?"
        )

    goal = script.goal or "наше предложение"
    return FALLBACK_TEXT.format(goal=goal)


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
        logger.warning("Inbound listener started for account %s", account.id)


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
                select(Contact).where(Contact.telegram_user_id == telegram_user_id)
            )
            contact: Contact | None = result.scalar_one_or_none()
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

            # 7.5 Inbound account limit guards
            settings = get_settings()
            daily_limit = getattr(settings, "daily_message_limit", None) or 50
            account_result = await db.execute(
                select(TelegramAccount).where(TelegramAccount.id == account.id)
            )
            db_account = account_result.scalar_one_or_none() or account

            current_daily = getattr(db_account, "daily_messages_sent", 0) or 0
            if current_daily >= daily_limit:
                logger.warning(
                    "Account %s reached daily limit (%s), skipping inbound reply",
                    account.id,
                    daily_limit,
                )
                return

            last_message_at = getattr(db_account, "last_message_at", None)
            if last_message_at is not None:
                if last_message_at.tzinfo is None:
                    last_message_at = last_message_at.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - last_message_at).total_seconds()
                if elapsed < 30:
                    logger.info(
                        "Account %s is rate limited for inbound reply (%.1fs since last message)",
                        account.id,
                        elapsed,
                    )
                    return

            # 8. Classify intent
            engine = LLMEngine()
            intent = await classify_intent(text, engine)

            # 8.5 Update funnel stage based on intent
            conversation.conversation_stage = next_stage(
                script,
                getattr(conversation, "conversation_stage", None) or "hook",
                intent,
            )

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

            if text.strip() and set(text.strip()) <= PUNCTUATION_ONLY_CHARS:
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

            # 14. Update conversation state / facts / sentiment
            event_map = {
                "meeting_intent": "meeting_intent",
                "positive": "positive_reply",
                "negative": "negative_reply",
                "objection": "objection",
                "question": "informational",
                "informational": "informational",
            }
            event = event_map.get(intent, "positive_reply")
            previous_state = conversation.current_state or "cold"
            new_state = transition(previous_state, event)
            conversation.current_state = new_state
            conversation.sentiment = (
                "positive"
                if intent in ("positive", "meeting_intent")
                else "negative"
                if intent == "negative"
                else "neutral"
            )
            current_facts = dict(conversation.facts_extracted or {})
            current_facts["last_intent"] = intent
            conversation.facts_extracted = current_facts
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
