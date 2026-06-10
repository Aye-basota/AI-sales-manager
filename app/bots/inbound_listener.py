"""Inbound message listener using Pyrogram."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from pyrogram import Client
    from pyrogram.types import Message

    _PYROGRAM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYROGRAM_AVAILABLE = False

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.db.redis import get_redis, invalidate_conversation_cache
from app.models.telegram_account import TelegramAccount
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.campaign import Campaign, CampaignContact
from app.models.script import Script
from app.bots.seller_client import SellerClient
from app.llm.engine import LLMEngine
from app.llm.intent_classifier import classify_intent
from app.llm.prompts import build_system_prompt, build_user_prompt
from app.core.humanizer import calculate_typing_delay, calculate_thinking_delay
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


async def start_inbound_listeners(db_session: AsyncSession | None = None) -> None:
    """Load ready/active accounts and start Pyrogram inbound listeners."""
    if not _PYROGRAM_AVAILABLE:
        logger.warning("Pyrogram not available, inbound listeners not started")
        return

    if db_session is None:
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(TelegramAccount).where(TelegramAccount.status.in_(["ready", "active"]))
            )
            accounts = result.scalars().all()
    else:
        result = await db_session.execute(
            select(TelegramAccount).where(TelegramAccount.status.in_(["ready", "active"]))
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
                select(Contact).where(Contact.telegram_user_id == telegram_user_id)
            )
            contact: Contact | None = result.scalar_one_or_none()
            if not contact:
                logger.info("Creating new contact for telegram_user_id %s", telegram_user_id)
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

            # 4.5 Update campaign contact status and analytics
            cc_result = await db.execute(
                select(CampaignContact)
                .where(CampaignContact.contact_id == contact.id)
                .where(CampaignContact.campaign_id == campaign.id)
            )
            campaign_contact = cc_result.scalar_one_or_none()
            if campaign_contact and campaign_contact.status in ("pending", "initial_sent", "follow_up_sent"):
                campaign_contact.status = "replied"
                campaign_contact.reply_received_at = datetime.now(timezone.utc)
                campaign.replied_count = (campaign.replied_count or 0) + 1
                await db.commit()

            if campaign.status not in ("running",):
                logger.info(
                    "Campaign %s is not running (%s), skipping automated reply",
                    campaign.id,
                    campaign.status,
                )
                return

            # 5. Mark message as read immediately (double-checks for lead)
            user_id = int(contact.telegram_user_id)
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

            # 8. Classify intent
            engine = LLMEngine()
            intent = await classify_intent(text, engine)

            # 9. Build context
            context = await get_conversation_context(db, conversation.id, limit=10)

            # 10. Generate response
            system_prompt = build_system_prompt(script)

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

            user_prompt = build_user_prompt(
                conversation_history=history,
                lead_facts=context["facts"] or {},
                last_agent_message=last_agent_msg,
                lead_message=text,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Show "online" before generation so the lead sees we are active
            await client.set_online()

            last_outbound = [
                msg.content for msg in context["messages"] if msg.direction == "outbound"
            ]

            try:
                response = await engine.generate_response_with_guardrails(
                    messages, last_messages=last_outbound, max_retries=1
                )
            except Exception as exc:
                logger.exception("LLM generation failed: %s", exc)
                response = {"text": "", "model": None, "tokens_used": 0}

            response_text = response.get("text", "")

            # If guardrails blocked even the retry, use fallback text
            if not response_text or response.get("model") == "fallback":
                goal = script.goal or "наше предложение"
                response_text = FALLBACK_TEXT.format(goal=goal)

            # 11. Humanizer delays
            typing_delay = calculate_typing_delay(response_text)
            thinking_delay = calculate_thinking_delay()

            # 12. Send with human-like delays
            # "typing" indicator should appear right before the typing delay
            await client.set_typing(user_id)
            await asyncio.sleep(thinking_delay / 1000.0)
            await client.send_message(
                user_id=user_id,
                text=response_text,
                typing_delay_ms=typing_delay,
            )

            # 13. Save outbound message
            await add_message(
                db,
                conversation.id,
                "outbound",
                response_text,
                message_type="text",
                llm_model=response.get("model"),
                tokens_used=response.get("tokens_used"),
                typing_delay_ms=typing_delay + thinking_delay,
                intent_classification=intent,
            )

            # 14. Update conversation state / facts / sentiment
            event_map = {
                "meeting_intent": "meeting_intent",
                "positive": "positive_reply",
                "negative": "negative_reply",
                "objection": "objection",
                "informational": "informational",
            }
            event = event_map.get(intent, "positive_reply")
            new_state = transition(conversation.current_state or "cold", event)
            conversation.current_state = new_state
            conversation.sentiment = (
                "positive"
                if intent in ("positive", "meeting_intent")
                else "negative" if intent == "negative" else "neutral"
            )
            current_facts = dict(conversation.facts_extracted or {})
            current_facts["last_intent"] = intent
            conversation.facts_extracted = current_facts
            await db.commit()

            # 15. Notify if hot lead
            if intent == "meeting_intent" or new_state in ("hot", "meeting_booked"):
                notif = NotificationService()
                await notif.send_hot_lead_alert(contact, conversation, last_message_text=text)

        except Exception as exc:
            logger.exception("Error handling inbound message from %s: %s", telegram_user_id, exc)
