"""Business logic for conversations and messages."""

import json
import logging
import types
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import (
    get_redis,
    cache_conversation_context,
    get_cached_conversation_context,
    invalidate_conversation_cache,
)
from app.models.conversation import Conversation, Message

try:
    from app.llm.engine import LLMEngine
except Exception:  # pragma: no cover
    LLMEngine = None  # type: ignore

logger = logging.getLogger(__name__)


async def get_conversation_context(
    db: AsyncSession,
    conversation_id: UUID,
    limit: int = 10,
) -> dict[str, Any]:
    """Fetch the recent context for a conversation.

    Returns the last *limit* messages in chronological order together with
    the lead facts extracted so far.

    Args:
        db: Active SQLAlchemy async session.
        conversation_id: UUID of the conversation.
        limit: Maximum number of recent messages to retrieve.

    Returns:
        A dictionary with keys ``messages`` (list of ``Message``) and
        ``facts`` (dict of extracted facts).
    """
    try:
        redis = await get_redis()
        cached = await get_cached_conversation_context(redis, conversation_id)
        if cached is not None:
            messages = [types.SimpleNamespace(**m) for m in cached["messages"]]
            return {"messages": messages, "facts": cached.get("facts", {})}
    except Exception:
        logger.warning(
            "Redis cache read failed for conversation %s",
            conversation_id,
            exc_info=True,
        )

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))

    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    facts = conversation.facts_extracted if conversation else {}

    result = {"messages": messages, "facts": facts}

    try:
        redis = await get_redis()
        await cache_conversation_context(
            redis, conversation_id, result["messages"], result["facts"]
        )
    except Exception:
        logger.warning(
            "Redis cache write failed for conversation %s",
            conversation_id,
            exc_info=True,
        )

    return result


async def add_message(
    db: AsyncSession,
    conversation_id: UUID,
    direction: str,
    content: str,
    **kwargs: Any,
) -> Message:
    """Persist a new message and update the conversation timestamp.

    Args:
        db: Active SQLAlchemy async session.
        conversation_id: UUID of the conversation.
        direction: Message direction (e.g. ``inbound`` or ``outbound``).
        content: Text content of the message.
        **kwargs: Additional fields accepted by the ``Message`` model.

    Returns:
        The newly created ``Message`` instance.
    """
    message = Message(
        conversation_id=conversation_id,
        direction=direction,
        content=content,
        **kwargs,
    )
    db.add(message)

    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation:
        conversation.last_message_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(message)

    try:
        redis = await get_redis()
        await invalidate_conversation_cache(redis, conversation_id)
    except Exception:
        logger.warning(
            "Redis cache invalidation failed for conversation %s",
            conversation_id,
            exc_info=True,
        )

    return message


async def update_lead_facts(
    db: AsyncSession,
    conversation_id: UUID,
    facts: dict[str, Any],
) -> Conversation:
    """Merge new facts into an existing conversation's extracted facts.

    Args:
        db: Active SQLAlchemy async session.
        conversation_id: UUID of the conversation.
        facts: Dictionary of new facts to merge.

    Returns:
        The updated ``Conversation`` instance.

    Raises:
        ValueError: If the conversation does not exist.
    """
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ValueError(f"Conversation {conversation_id} not found")

    current_facts: dict[str, Any] = dict(conversation.facts_extracted or {})
    current_facts.update(facts)
    conversation.facts_extracted = current_facts

    await db.commit()
    await db.refresh(conversation)

    try:
        redis = await get_redis()
        await invalidate_conversation_cache(redis, conversation_id)
    except Exception:
        logger.warning(
            "Redis cache invalidation failed for conversation %s",
            conversation_id,
            exc_info=True,
        )

    return conversation


_FACT_EXTRACTION_PROMPT = (
    "Ты — ассистент по извлечению фактов из переписки менеджера по продажам с потенциальным клиентом.\n"
    "Извлеки из следующего сообщения клиента ВСЕ, что можно понять о клиенте.\n"
    "Верни ТОЛЬКО JSON объект с полями (используй пустую строку, если не удалось определить):\n"
    "{{\n"
    '  "company": "название компании или пусто",\n'
    '  "role": "должность или пусто",\n'
    '  "pain": "проблема/потребность или пусто",\n'
    '  "budget": "упоминание бюджета или пусто",\n'
    '  "city": "город или пусто",\n'
    '  "industry": "сфера деятельности или пусто"\n'
    "}}\n\n"
    "Сообщение клиента:\n{message}\n\n"
    "JSON:"
)


async def extract_facts_from_message(message_text: str) -> dict[str, Any]:
    """Extract structured facts from a lead's inbound message.

    Uses the configured LLM engine.  If the call fails or the response is not
    valid JSON, an empty dictionary is returned.
    """
    if not message_text or not message_text.strip():
        return {}

    if LLMEngine is None:
        return {}

    engine = LLMEngine()
    prompt = _FACT_EXTRACTION_PROMPT.format(message=message_text)
    messages = [
        {"role": "system", "content": "Ты возвращаешь только JSON."},
        {"role": "user", "content": prompt},
    ]

    try:
        result = await engine.generate_with_fallback(messages)
        text = result.get("text", "")
        if not text:
            return {}

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        facts = json.loads(text)
        if not isinstance(facts, dict):
            return {}
        return {k: v for k, v in facts.items() if v}
    except Exception as exc:
        logger.debug("Fact extraction failed: %s", exc)
        return {}
