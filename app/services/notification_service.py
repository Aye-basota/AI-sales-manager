"""Operator notification stubs.

In a production deployment these functions would send real-time alerts
(e.g. Telegram messages) to the sales team.
"""

import logging

from app.models import Contact, Conversation

logger = logging.getLogger(__name__)


async def notify_operator_hot_lead(contact: Contact, conversation: Conversation) -> None:
    """Notify operators that a hot lead has been identified.

    Args:
        contact: The contact that triggered the hot-lead rule.
        conversation: The related conversation.
    """
    logger.info(
        "[NOTIFICATION] Hot lead detected - contact_id=%s conversation_id=%s",
        contact.id,
        conversation.id,
    )


async def notify_operator_meeting_booked(contact: Contact, conversation: Conversation) -> None:
    """Notify operators that a meeting has been booked with a lead.

    Args:
        contact: The contact that booked the meeting.
        conversation: The related conversation.
    """
    logger.info(
        "[NOTIFICATION] Meeting booked - contact_id=%s conversation_id=%s",
        contact.id,
        conversation.id,
    )
