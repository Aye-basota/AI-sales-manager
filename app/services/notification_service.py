"""Operator notification service.

Sends real-time alerts (Telegram messages) to the sales team via Admin Bot.
"""

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import get_settings
from app.models import Contact, Conversation

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    """Service for sending operator notifications via Telegram."""

    def __init__(self, bot: Bot | None = None, chat_id: str | None = None):
        self._bot = bot
        self._chat_id = chat_id or settings.admin_notification_chat_id

    def _get_bot(self) -> Bot | None:
        if self._bot is None:
            if not settings.admin_bot_token:
                return None
            self._bot = Bot(token=settings.admin_bot_token)
        return self._bot

    async def send_hot_lead_alert(
        self,
        contact: Contact,
        conversation: Conversation,
        last_message_text: str = "",
    ) -> None:
        """Send a hot-lead alert to the admin notification chat.

        Args:
            contact: The contact that triggered the hot-lead rule.
            conversation: The related conversation.
            last_message_text: The last message text to include in the alert.
        """
        if not self._chat_id:
            logger.warning("ADMIN_NOTIFICATION_CHAT_ID is not set, hot lead alert not sent.")
            return

        bot = self._get_bot()
        if not bot:
            logger.warning("ADMIN_BOT_TOKEN is not set, cannot send alert.")
            return

        text = (
            f"🔥 Hot Lead\n"
            f"Имя: {contact.first_name or 'N/A'}\n"
            f"Компания: {contact.company_name or 'N/A'}\n"
            f"Последнее сообщение: {last_message_text or 'N/A'}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Посмотреть диалог",
                        callback_data=f"dialog:{conversation.id}",
                    )
                ]
            ]
        )
        try:
            await bot.send_message(chat_id=self._chat_id, text=text, reply_markup=kb)
        except Exception:
            logger.exception("Failed to send hot lead alert")

    async def send_meeting_booked_alert(
        self,
        contact: Contact,
        conversation: Conversation,
    ) -> None:
        """Send a meeting-booked alert to the admin notification chat.

        Args:
            contact: The contact that booked the meeting.
            conversation: The related conversation.
        """
        if not self._chat_id:
            logger.warning("ADMIN_NOTIFICATION_CHAT_ID is not set, meeting booked alert not sent.")
            return

        bot = self._get_bot()
        if not bot:
            logger.warning("ADMIN_BOT_TOKEN is not set, cannot send alert.")
            return

        text = (
            f"📅 Meeting Booked\n"
            f"Имя: {contact.first_name or 'N/A'}\n"
            f"Компания: {contact.company_name or 'N/A'}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Посмотреть диалог",
                        callback_data=f"dialog:{conversation.id}",
                    )
                ]
            ]
        )
        try:
            await bot.send_message(chat_id=self._chat_id, text=text, reply_markup=kb)
        except Exception:
            logger.exception("Failed to send meeting booked alert")


_service = NotificationService()


async def notify_operator_hot_lead(contact: Contact, conversation: Conversation) -> None:
    """Notify operators that a hot lead has been identified.

    Backward-compatible wrapper around :class:`NotificationService`.

    Args:
        contact: The contact that triggered the hot-lead rule.
        conversation: The related conversation.
    """
    await _service.send_hot_lead_alert(contact, conversation)


async def notify_operator_meeting_booked(contact: Contact, conversation: Conversation) -> None:
    """Notify operators that a meeting has been booked with a lead.

    Backward-compatible wrapper around :class:`NotificationService`.

    Args:
        contact: The contact that booked the meeting.
        conversation: The related conversation.
    """
    await _service.send_meeting_booked_alert(contact, conversation)
