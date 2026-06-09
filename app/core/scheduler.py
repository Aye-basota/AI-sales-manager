"""Campaign scheduling and anti-spam logic."""

import logging
from datetime import datetime, timedelta, time
from typing import Protocol

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def should_send_to_contact(
    contact_status: str,
    last_sent_at: datetime | None,
    follow_up_delay_hours: int,
    now: datetime,
) -> bool:
    """Return True if a message may be sent to the contact now.

    *contact_status* is the campaign-contact status (e.g. ``pending``,
    ``sent``, ``follow_up_sent``).
    *last_sent_at* is the timestamp of the most recent outbound message.
    """
    if contact_status == "pending":
        return True

    if contact_status in ("sent", "initial_sent", "follow_up_sent"):
        if last_sent_at is None:
            return True
        delay = timedelta(hours=follow_up_delay_hours)
        return now >= last_sent_at + delay

    return False


def is_within_working_hours(
    timezone_str: str,
    working_start: time,
    working_end: time,
    now: datetime,
) -> bool:
    """Return True if *now* falls within working hours in the given timezone.

    The timezone string is currently accepted for API compatibility but
    the comparison is performed on the *localised* ``now`` value passed
    by the caller.
    """
    current_time = now.time()
    if working_start <= working_end:
        return working_start <= current_time <= working_end
    # Handles overnight shifts (not expected for 9-18 but kept robust)
    return current_time >= working_start or current_time <= working_end


class _HasContactAttrs(Protocol):
    status: str
    initial_sent_at: datetime | None
    follow_up_sent_at: datetime | None
    message_count: int


class _HasScriptAttrs(Protocol):
    max_messages: int
    follow_up_delay_hours: int
    working_hours_start: time
    working_hours_end: time
    timezone: str


def next_contact_to_process(
    campaign_contacts: list[_HasContactAttrs],
    script: _HasScriptAttrs,
    now: datetime,
) -> list[_HasContactAttrs]:
    """Return contacts that are ready to receive a message right now.

    Filters apply anti-spam rules:
    - max *script.max_messages* messages per contact,
    - only during working hours,
    - follow-ups respect *follow_up_delay_hours*.
    """
    if not is_within_working_hours(
        script.timezone,
        script.working_hours_start,
        script.working_hours_end,
        now,
    ):
        return []

    ready: list[_HasContactAttrs] = []
    for contact in campaign_contacts:
        if contact.message_count >= script.max_messages:
            continue

        last_sent = contact.follow_up_sent_at or contact.initial_sent_at
        if should_send_to_contact(
            contact.status,
            last_sent,
            script.follow_up_delay_hours,
            now,
        ):
            ready.append(contact)

    return ready


# ---------------------------------------------------------------------------
# Campaign processing
# ---------------------------------------------------------------------------


async def process_campaigns(db_session: AsyncSession) -> None:
    """Process all running campaigns.

    For each running campaign:
      1. Load its script and check working hours.
      2. Find campaign contacts with status ``pending`` or ``initial_sent``.
      3. Filter contacts that are ready (respecting delays / max messages).
      4. For each ready contact find or create a conversation.
      5. Select a Telegram account (rate-limited to 1 msg / 30 s).
      6. Dispatch ``send_initial_message`` or ``send_follow_up_message``.
      7. Commit the session after each contact.
    """
    from app.models.campaign import Campaign, CampaignContact
    from app.models.script import Script
    from app.models.contact import Contact
    from app.models.telegram_account import TelegramAccount
    from app.models.conversation import Conversation
    from app.core.account_manager import select_account

    now = datetime.now()

    campaigns_result = await db_session.execute(
        select(Campaign).where(Campaign.status == "running")
    )
    campaigns = campaigns_result.scalars().all()

    for campaign in campaigns:
        script_result = await db_session.execute(
            select(Script).where(Script.id == campaign.script_id)
        )
        script = script_result.scalar_one_or_none()
        if not script:
            continue

        if not is_within_working_hours(
            script.timezone,
            script.working_hours_start,
            script.working_hours_end,
            now,
        ):
            continue

        cc_result = await db_session.execute(
            select(CampaignContact)
            .where(CampaignContact.campaign_id == campaign.id)
            .where(CampaignContact.status.in_(["pending", "initial_sent"]))
        )
        campaign_contacts = cc_result.scalars().all()

        ready_contacts = next_contact_to_process(campaign_contacts, script, now)

        for cc in ready_contacts:
            contact_result = await db_session.execute(
                select(Contact).where(Contact.id == cc.contact_id)
            )
            contact = contact_result.scalar_one_or_none()
            if not contact:
                continue

            if not contact.telegram_user_id:
                logger.debug(
                    "Skipping contact %s (no telegram_user_id)", contact.id
                )
                continue

            conv_result = await db_session.execute(
                select(Conversation)
                .where(Conversation.contact_id == contact.id)
                .where(Conversation.campaign_id == campaign.id)
            )
            conversation = conv_result.scalar_one_or_none()
            if conversation is None:
                conversation = Conversation(
                    contact_id=contact.id,
                    campaign_id=campaign.id,
                    current_state="cold",
                )
                db_session.add(conversation)

            # Select account
            if contact.assigned_account_id:
                acc_result = await db_session.execute(
                    select(TelegramAccount).where(
                        TelegramAccount.id == contact.assigned_account_id
                    )
                )
                account = acc_result.scalar_one_or_none()
            else:
                acc_result = await db_session.execute(
                    select(TelegramAccount).where(
                        TelegramAccount.status.in_(["ready", "active"])
                    )
                )
                accounts = acc_result.scalars().all()
                account = select_account(accounts)

            if account is None:
                logger.warning(
                    "No eligible account for contact %s", contact.id
                )
                continue

            # Rate limit: 1 message per 30 seconds per account
            if account.last_message_at is not None:
                elapsed = (now - account.last_message_at).total_seconds()
                if elapsed < 30:
                    logger.debug(
                        "Account %s rate limited (%.1f s since last msg)",
                        account.id,
                        elapsed,
                    )
                    continue

            try:
                if cc.status == "pending":
                    await send_initial_message(
                        db_session=db_session,
                        campaign_contact=cc,
                        contact=contact,
                        conversation=conversation,
                        script=script,
                        account=account,
                    )
                elif cc.status == "initial_sent":
                    await send_follow_up_message(
                        db_session=db_session,
                        campaign_contact=cc,
                        contact=contact,
                        conversation=conversation,
                        script=script,
                        account=account,
                    )
                else:
                    continue
            except Exception as exc:
                logger.exception(
                    "Error sending message to contact %s: %s", contact.id, exc
                )
                continue

            await db_session.commit()


async def send_initial_message(
    db_session: AsyncSession,
    campaign_contact,
    contact,
    conversation,
    script,
    account,
) -> None:
    """Generate, guardrail, humanise and send an initial outbound message."""
    from app.llm.engine import LLMEngine
    from app.llm.prompts import build_system_prompt
    from app.llm.guardrails import apply_guardrails
    from app.core.humanizer import (
        calculate_typing_delay,
        calculate_thinking_delay,
        maybe_self_correct,
        add_casual_markers,
        maybe_double_take,
    )
    from app.bots.seller_client import SellerClient
    from app.core.account_manager import mark_message_sent
    from app.core.state_machine import transition
    from app.models.conversation import Message

    engine = LLMEngine()

    system_prompt = build_system_prompt(script)
    user_prompt_parts = [
        "Напиши первое сообщение для потенциального клиента."
    ]
    if contact.first_name:
        user_prompt_parts.append(f"Имя: {contact.first_name}")
    if contact.company_name:
        user_prompt_parts.append(f"Компания: {contact.company_name}")
    if contact.position:
        user_prompt_parts.append(f"Должность: {contact.position}")
    if contact.city:
        user_prompt_parts.append(f"Город: {contact.city}")
    if contact.industry:
        user_prompt_parts.append(f"Индустрия: {contact.industry}")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(user_prompt_parts)},
    ]

    try:
        response = await engine.generate_with_fallback(messages)
    except Exception as exc:
        logger.exception("LLM generation failed for initial message: %s", exc)
        raise

    text = response.get("text", "")
    if not text:
        raise RuntimeError("LLM returned empty text")

    text = apply_guardrails(text, [])
    if text is None:
        raise RuntimeError("Guardrails blocked the initial message")

    text = maybe_self_correct(text)
    text = add_casual_markers(text)
    text = maybe_double_take(text, getattr(contact, "city", None))

    typing_delay = calculate_typing_delay(text)
    thinking_delay = calculate_thinking_delay()
    total_delay = typing_delay + thinking_delay

    client = SellerClient(
        account_id=str(account.id),
        session_string=account.session_string or "",
        proxy_url=account.proxy_url,
    )
    try:
        await client.start()
        await client.send_message(
            user_id=int(contact.telegram_user_id),
            text=text,
            typing_delay_ms=total_delay,
        )
    finally:
        await client.stop()

    # Update campaign contact
    campaign_contact.status = "initial_sent"
    campaign_contact.initial_sent_at = datetime.now()
    campaign_contact.message_count = (campaign_contact.message_count or 0) + 1

    # Update account
    mark_message_sent(account)
    account.last_message_at = datetime.now()

    # Update conversation state
    conversation.current_state = transition(
        conversation.current_state or "cold", "initial_message"
    )
    conversation.last_message_at = datetime.now()

    # Persist outbound message
    message = Message(
        conversation_id=conversation.id,
        direction="outbound",
        content=text,
        message_type="text",
        llm_model=response.get("model"),
        tokens_used=response.get("tokens_used"),
        typing_delay_ms=total_delay,
    )
    db_session.add(message)

    try:
        from app.db.redis import get_redis, invalidate_conversation_cache

        redis = await get_redis()
        await invalidate_conversation_cache(redis, conversation.id)
    except Exception:
        pass


async def send_follow_up_message(
    db_session: AsyncSession,
    campaign_contact,
    contact,
    conversation,
    script,
    account,
) -> None:
    """Generate, guardrail, humanise and send a follow-up outbound message."""
    from app.llm.engine import LLMEngine
    from app.llm.prompts import build_system_prompt, build_user_prompt
    from app.llm.guardrails import apply_guardrails
    from app.core.humanizer import (
        calculate_typing_delay,
        calculate_thinking_delay,
        maybe_self_correct,
        add_casual_markers,
        maybe_double_take,
    )
    from app.bots.seller_client import SellerClient
    from app.core.account_manager import mark_message_sent
    from app.core.state_machine import transition
    from app.models.conversation import Message
    from app.services.conversation_service import get_conversation_context

    engine = LLMEngine()

    context = await get_conversation_context(
        db_session, conversation.id, limit=10
    )

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
        lead_message="",
    )
    user_prompt = (
        "Напиши короткое follow-up сообщение. Клиент пока не ответил.\n\n"
        + user_prompt
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await engine.generate_with_fallback(messages)
    except Exception as exc:
        logger.exception("LLM generation failed for follow-up message: %s", exc)
        raise

    text = response.get("text", "")
    if not text:
        raise RuntimeError("LLM returned empty text")

    last_outbound = [
        msg.content for msg in context["messages"] if msg.direction == "outbound"
    ]
    text = apply_guardrails(text, last_outbound)
    if text is None:
        raise RuntimeError("Guardrails blocked the follow-up message")

    text = maybe_self_correct(text)
    text = add_casual_markers(text)
    text = maybe_double_take(text, getattr(contact, "city", None))

    typing_delay = calculate_typing_delay(text)
    thinking_delay = calculate_thinking_delay()
    total_delay = typing_delay + thinking_delay

    client = SellerClient(
        account_id=str(account.id),
        session_string=account.session_string or "",
        proxy_url=account.proxy_url,
    )
    try:
        await client.start()
        await client.send_message(
            user_id=int(contact.telegram_user_id),
            text=text,
            typing_delay_ms=total_delay,
        )
    finally:
        await client.stop()

    # Update campaign contact
    campaign_contact.status = "follow_up_sent"
    campaign_contact.follow_up_sent_at = datetime.now()
    campaign_contact.message_count = (campaign_contact.message_count or 0) + 1

    # Update account
    mark_message_sent(account)
    account.last_message_at = datetime.now()

    # Update conversation state
    conversation.current_state = transition(
        conversation.current_state or "cold", "no_reply_24h"
    )
    conversation.last_message_at = datetime.now()

    # Persist outbound message
    message = Message(
        conversation_id=conversation.id,
        direction="outbound",
        content=text,
        message_type="text",
        llm_model=response.get("model"),
        tokens_used=response.get("tokens_used"),
        typing_delay_ms=total_delay,
    )
    db_session.add(message)

    try:
        from app.db.redis import get_redis, invalidate_conversation_cache

        redis = await get_redis()
        await invalidate_conversation_cache(redis, conversation.id)
    except Exception:
        pass


class CampaignScheduler:
    """APScheduler wrapper that processes running campaigns every 5 minutes."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self._scheduler.add_job(
            self._run_process_campaigns,
            trigger=IntervalTrigger(minutes=5),
            id="process_campaigns",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("CampaignScheduler started")

    def shutdown(self) -> None:
        self._scheduler.shutdown()
        logger.info("CampaignScheduler shutdown")

    async def _run_process_campaigns(self) -> None:
        from app.db.session import AsyncSessionLocal

        try:
            async with AsyncSessionLocal() as session:
                await process_campaigns(session)
        except Exception as exc:
            logger.exception("process_campaigns job failed: %s", exc)
