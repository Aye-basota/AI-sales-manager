"""Campaign scheduling and anti-spam logic."""

import logging
import random
from datetime import datetime, timedelta, time, timezone
from typing import Protocol
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)



try:
    import asyncio

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        _tmp_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_tmp_loop)

    from pyrogram.errors import FloodWait, PeerFlood

    _PYROGRAM_ERRORS_AVAILABLE = True
except ImportError:  # pragma: no cover
    FloodWait = Exception
    PeerFlood = Exception
    _PYROGRAM_ERRORS_AVAILABLE = False


class AccountFloodError(Exception):
    """Raised when a Telegram account hits a rate limit."""

    def __init__(self, account_id, wait_seconds: int = 3600) -> None:
        self.account_id = account_id
        self.wait_seconds = wait_seconds
        super().__init__(f"Account {account_id} flood error: wait {wait_seconds}s")


class AccountPeerFloodError(Exception):
    """Raised when a Telegram account hits PeerFlood."""

    def __init__(self, account_id) -> None:
        self.account_id = account_id
        super().__init__(f"Account {account_id} peer flood error")


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

    The ``now`` value is converted to the target timezone before the time
    comparison is performed.  This makes the scheduler robust when the
    server timezone differs from the campaign timezone.
    """
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = ZoneInfo("UTC")

    if now.tzinfo is None:
        # Naive datetime: assume it is already in the target timezone
        # (backward-compatible for unit tests and legacy callers)
        localized_now = now.replace(tzinfo=tz)
    else:
        localized_now = now.astimezone(tz)
    current_time = localized_now.time()

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
      7. On FloodWait / PeerFlood mark the account cooldown and retry once.
      8. Commit the session after each contact.
    """
    from app.models.campaign import Campaign, CampaignContact
    from app.models.script import Script
    from app.models.contact import Contact
    from app.models.telegram_account import TelegramAccount
    from app.models.conversation import Conversation
    from app.core.account_manager import (
        select_account,
        mark_account_cooldown,
    )

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

        now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

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
            now = datetime.now(timezone.utc)
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)

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
            elif conversation.current_state in ("hot", "meeting_booked", "closed"):
                logger.debug(
                    "Skipping contact %s: conversation already in terminal state %s",
                    contact.id,
                    conversation.current_state,
                )
                continue

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
                        TelegramAccount.status.in_(["ready", "active"]),
                        TelegramAccount.session_string.isnot(None),
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
                last_at = account.last_message_at
                if last_at.tzinfo is None:
                    last_at = last_at.replace(tzinfo=timezone.utc)
                elapsed = (now - last_at).total_seconds()
                if elapsed < 30:
                    logger.debug(
                        "Account %s rate limited (%.1f s since last msg)",
                        account.id,
                        elapsed,
                    )
                    continue

            async def _send_with_account(acc):
                if cc.status == "pending":
                    await send_initial_message(
                        db_session=db_session,
                        campaign_contact=cc,
                        contact=contact,
                        conversation=conversation,
                        script=script,
                        account=acc,
                    )
                elif cc.status == "initial_sent":
                    await send_follow_up_message(
                        db_session=db_session,
                        campaign_contact=cc,
                        contact=contact,
                        conversation=conversation,
                        script=script,
                        account=acc,
                    )

            try:
                await _send_with_account(account)
            except AccountFloodError as exc:
                logger.warning(
                    "Account %s hit FloodWait (%ss), marking cooldown",
                    exc.account_id,
                    exc.wait_seconds,
                )
                await mark_account_cooldown(
                    exc.account_id, db_session, wait_seconds=exc.wait_seconds
                )
                await db_session.commit()

                # Try once more with another account
                acc_result = await db_session.execute(
                    select(TelegramAccount).where(
                        TelegramAccount.status.in_(["ready", "active"]),
                        TelegramAccount.id != exc.account_id,
                    )
                )
                accounts = acc_result.scalars().all()
                retry_account = select_account(accounts)
                if retry_account is None:
                    logger.warning("No alternative account for contact %s", contact.id)
                    continue
                try:
                    await _send_with_account(retry_account)
                except AccountFloodError as exc2:
                    logger.warning(
                        "Alternative account %s also flood-limited", exc2.account_id
                    )
                    await mark_account_cooldown(
                        exc2.account_id, db_session, wait_seconds=exc2.wait_seconds
                    )
                    await db_session.commit()
                    continue
            except AccountPeerFloodError as exc:
                logger.warning(
                    "Account %s hit PeerFlood, marking cooldown 24h", exc.account_id
                )
                await mark_account_cooldown(
                    exc.account_id, db_session, wait_seconds=24 * 3600
                )
                await db_session.commit()

                acc_result = await db_session.execute(
                    select(TelegramAccount).where(
                        TelegramAccount.status.in_(["ready", "active"]),
                        TelegramAccount.id != exc.account_id,
                    )
                )
                accounts = acc_result.scalars().all()
                retry_account = select_account(accounts)
                if retry_account is None:
                    logger.warning("No alternative account for contact %s", contact.id)
                    continue
                try:
                    await _send_with_account(retry_account)
                except AccountPeerFloodError as exc2:
                    logger.warning(
                        "Alternative account %s also peer-flood-limited", exc2.account_id
                    )
                    await mark_account_cooldown(
                        exc2.account_id, db_session, wait_seconds=24 * 3600
                    )
                    await db_session.commit()
                    continue
            except Exception as exc:
                logger.exception(
                    "Error sending message to contact %s: %s", contact.id, exc
                )
                await db_session.rollback()
                continue

            campaign.processed_contacts = (campaign.processed_contacts or 0) + 1
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

    from app.llm.prompts import build_system_prompt
    from app.core.humanizer import (
        calculate_typing_delay,
        calculate_thinking_delay,
        maybe_self_correct,
        add_casual_markers,
        maybe_double_take,
        split_message_into_chunks,
    )

    from app.core.account_manager import mark_message_sent
    from app.core.state_machine import transition
    from app.models.conversation import Message

    from app.llm.engine import LLMEngine
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
        response = await engine.generate_response_with_guardrails(messages, [])
    except Exception as exc:
        logger.exception("LLM generation failed for initial message: %s", exc)
        raise

    text = response.get("text", "")
    if not text:
        raise RuntimeError("LLM returned empty text")

    text = maybe_self_correct(text)
    text = add_casual_markers(text)
    text = maybe_double_take(text, getattr(contact, "city", None))

    chunks = split_message_into_chunks(text)
    base_typing_delay = calculate_typing_delay(text)
    thinking_delay = calculate_thinking_delay()
    total_delay = base_typing_delay + thinking_delay
    chunk_delays = [
        int(base_typing_delay * len(chunk) / max(len(text), 1))
        for chunk in chunks
    ]

    from app.bots.seller_client import SellerClient
    settings = get_settings()
    client = SellerClient(
        account_id=str(account.id),
        session_string=account.session_string or "",
        proxy_url=account.proxy_url,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
    )
    try:
        await client.start()
        for idx, chunk in enumerate(chunks):
            if idx > 0:
                await asyncio.sleep(random.uniform(1.5, 3.5))
            await client.send_message(
                user_id=int(contact.telegram_user_id),
                text=chunk,
                typing_delay_ms=chunk_delays[idx] + thinking_delay if idx == 0 else chunk_delays[idx],
            )
            thinking_delay = 0
    except FloodWait as exc:
        wait_seconds = getattr(exc, "value", 60)
        logger.warning(
            "FloodWait on account %s for %ss", account.id, wait_seconds
        )
        raise AccountFloodError(account.id, wait_seconds=wait_seconds) from exc
    except PeerFlood as exc:
        logger.warning("PeerFlood on account %s", account.id)
        raise AccountPeerFloodError(account.id) from exc
    finally:
        await client.stop()

    # Update campaign contact
    campaign_contact.status = "initial_sent"
    campaign_contact.initial_sent_at = datetime.now(timezone.utc)
    campaign_contact.last_message_at = datetime.now(timezone.utc)
    campaign_contact.message_count = (campaign_contact.message_count or 0) + 1

    # Update account
    mark_message_sent(account)
    account.last_message_at = datetime.now(timezone.utc)

    # Update conversation state
    conversation.current_state = transition(
        conversation.current_state or "cold", "initial_message"
    )
    conversation.last_message_at = datetime.now(timezone.utc)

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

    from app.llm.prompts import build_system_prompt, build_user_prompt
    from app.core.humanizer import (
        calculate_typing_delay,
        calculate_thinking_delay,
        maybe_self_correct,
        add_casual_markers,
        maybe_double_take,
        split_message_into_chunks,
    )

    from app.core.account_manager import mark_message_sent
    from app.core.state_machine import transition
    from app.models.conversation import Message
    from app.services.conversation_service import get_conversation_context

    from app.llm.engine import LLMEngine
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
        response = await engine.generate_response_with_guardrails(
            messages,
            [
                msg.content
                for msg in context["messages"]
                if msg.direction == "outbound"
            ],
        )
    except Exception as exc:
        logger.exception("LLM generation failed for follow-up message: %s", exc)
        raise

    text = response.get("text", "")
    if not text:
        raise RuntimeError("LLM returned empty text")

    text = maybe_self_correct(text)
    text = add_casual_markers(text)
    text = maybe_double_take(text, getattr(contact, "city", None))

    chunks = split_message_into_chunks(text)
    base_typing_delay = calculate_typing_delay(text)
    thinking_delay = calculate_thinking_delay()
    total_delay = base_typing_delay + thinking_delay
    chunk_delays = [
        int(base_typing_delay * len(chunk) / max(len(text), 1))
        for chunk in chunks
    ]

    from app.bots.seller_client import SellerClient
    settings = get_settings()
    client = SellerClient(
        account_id=str(account.id),
        session_string=account.session_string or "",
        proxy_url=account.proxy_url,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
    )
    try:
        await client.start()
        for idx, chunk in enumerate(chunks):
            if idx > 0:
                await asyncio.sleep(random.uniform(1.5, 3.5))
            await client.send_message(
                user_id=int(contact.telegram_user_id),
                text=chunk,
                typing_delay_ms=chunk_delays[idx] + thinking_delay if idx == 0 else chunk_delays[idx],
            )
            thinking_delay = 0
    except FloodWait as exc:
        wait_seconds = getattr(exc, "value", 60)
        logger.warning(
            "FloodWait on account %s for %ss", account.id, wait_seconds
        )
        raise AccountFloodError(account.id, wait_seconds=wait_seconds) from exc
    except PeerFlood as exc:
        logger.warning("PeerFlood on account %s", account.id)
        raise AccountPeerFloodError(account.id) from exc
    finally:
        await client.stop()

    # Update campaign contact
    campaign_contact.status = "follow_up_sent"
    campaign_contact.follow_up_sent_at = datetime.now(timezone.utc)
    campaign_contact.last_message_at = datetime.now(timezone.utc)
    campaign_contact.message_count = (campaign_contact.message_count or 0) + 1

    # Update account
    mark_message_sent(account)
    account.last_message_at = datetime.now(timezone.utc)

    # Update conversation state
    conversation.current_state = transition(
        conversation.current_state or "cold", "no_reply_24h"
    )
    conversation.last_message_at = datetime.now(timezone.utc)

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


# ---------------------------------------------------------------------------
# Auto-close stale conversations
# ---------------------------------------------------------------------------


async def auto_close_conversations(db_session: AsyncSession) -> None:
    """Close campaign contacts that have not replied within 48 hours.

    Moves ``CampaignContact`` rows with status ``follow_up_sent`` and
    ``follow_up_sent_at`` older than 48 hours to ``closed``, and updates
    the corresponding ``Conversation`` state via the state machine.
    """
    from app.models.campaign import CampaignContact
    from app.models.conversation import Conversation
    from app.core.state_machine import transition

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    result = await db_session.execute(
        select(CampaignContact)
        .where(CampaignContact.status == "follow_up_sent")
        .where(CampaignContact.follow_up_sent_at < cutoff)
    )
    stale_contacts = result.scalars().all()

    for cc in stale_contacts:
        cc.status = "closed"

        conv_result = await db_session.execute(
            select(Conversation).where(
                Conversation.contact_id == cc.contact_id,
                Conversation.campaign_id == cc.campaign_id,
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if conversation:
            conversation.current_state = transition(
                conversation.current_state or "cold", "no_reply_48h"
            )
            conversation.last_message_at = datetime.now(timezone.utc)

    await db_session.commit()


# ---------------------------------------------------------------------------
# Scheduler wrapper
# ---------------------------------------------------------------------------


def _get_sync_db_url() -> str:
    """Derive a synchronous SQLAlchemy URL from the async one for APScheduler."""
    settings = get_settings()
    url = settings.database_url
    # APScheduler's SQLAlchemyJobStore requires a synchronous driver.
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class CampaignScheduler:
    """APScheduler wrapper that processes running campaigns and maintains resilience."""

    def __init__(self) -> None:
        jobstores = {
            "default": SQLAlchemyJobStore(url=_get_sync_db_url())
        }
        self._scheduler = AsyncIOScheduler(jobstores=jobstores)

    def start(self) -> None:
        self._scheduler.add_job(
            self._run_process_campaigns,
            trigger=IntervalTrigger(minutes=5),
            id="process_campaigns",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._run_reset_daily_counters,
            trigger=CronTrigger(hour=0, minute=0, timezone="Europe/Moscow"),
            id="reset_daily_counters",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._run_recover_cooldown_accounts,
            trigger=IntervalTrigger(hours=6),
            id="recover_cooldown_accounts",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._run_auto_close_conversations,
            trigger=IntervalTrigger(hours=6),
            id="auto_close_conversations",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("CampaignScheduler started")

    def shutdown(self, wait: bool = True) -> None:
        self._scheduler.shutdown(wait=wait)
        logger.info("CampaignScheduler shutdown")

    def is_running(self) -> bool:
        return getattr(self._scheduler, "running", False)

    @staticmethod
    async def _run_process_campaigns() -> None:


        try:
            async with AsyncSessionLocal() as session:
                await process_campaigns(session)
        except Exception as exc:
            logger.exception("process_campaigns job failed: %s", exc)

    @staticmethod
    async def _run_reset_daily_counters() -> None:

        from app.core.account_manager import reset_daily_counters_db

        try:
            async with AsyncSessionLocal() as session:
                await reset_daily_counters_db(session)
                logger.info("Daily counters reset")
        except Exception as exc:
            logger.exception("reset_daily_counters job failed: %s", exc)

    @staticmethod
    async def _run_recover_cooldown_accounts() -> None:

        from app.core.account_manager import recover_cooldown_accounts

        try:
            async with AsyncSessionLocal() as session:
                await recover_cooldown_accounts(session)
                logger.info("Cooldown accounts recovered")
        except Exception as exc:
            logger.exception("recover_cooldown_accounts job failed: %s", exc)

    @staticmethod
    async def _run_auto_close_conversations() -> None:


        try:
            async with AsyncSessionLocal() as session:
                await auto_close_conversations(session)
                logger.info("Auto-closed stale conversations")
        except Exception as exc:
            logger.exception("auto_close_conversations job failed: %s", exc)


# Module-level singleton used by main.py and the health endpoint.
scheduler = CampaignScheduler()
