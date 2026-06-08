"""Business logic for conversations and messages."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message


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

    return {"messages": messages, "facts": facts}


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
    return conversation
