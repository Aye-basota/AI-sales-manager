"""Operator notification service.

Sends real-time alerts (Telegram messages) to the sales team via Admin Bot.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import get_settings
from app.models import Contact, Conversation

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_RETRIES = 3


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

    async def _send_with_retry(self, bot: Bot, **kwargs) -> None:
        """Send a Telegram message with retry logic.

        Retries on ``TelegramRetryAfter`` (honouring the server's suggested
        delay) and on generic ``TelegramAPIError`` (exponential backoff).
        """
        for attempt in range(_MAX_RETRIES + 1):
            try:
                await bot.send_message(**kwargs)
                return
            except TelegramRetryAfter as exc:
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "Telegram rate limited, retrying after %s seconds (attempt %d/%d)",
                        exc.retry_after,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    await asyncio.sleep(exc.retry_after)
                else:
                    raise
            except TelegramAPIError:
                if attempt < _MAX_RETRIES:
                    wait = min(2 ** attempt, 8)
                    logger.warning(
                        "Telegram API error, retrying in %ss (attempt %d/%d)",
                        wait,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

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

        status_label = "Согласился на созвон" if conversation.current_state == "meeting_booked" else "Горячий лид"
        text = (
            f"🔥 Новый Hot Lead!\n"
            f"{contact.first_name or ''} {contact.last_name or ''}, {contact.company_name or 'N/A'}\n"
            f"Статус: {status_label}\n"
            f"Сообщение: {last_message_text or 'N/A'}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📋 Диалог", callback_data=f"dialog:{conversation.id}"),
                    InlineKeyboardButton(text="✅ Qualified", callback_data=f"qualify:{conversation.id}"),
                    InlineKeyboardButton(text="❌ Rejected", callback_data=f"reject:{conversation.id}"),
                ]
            ]
        )
        try:
            await self._send_with_retry(bot, chat_id=self._chat_id, text=text, reply_markup=kb)
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
                    InlineKeyboardButton(text="📋 Диалог", callback_data=f"dialog:{conversation.id}"),
                    InlineKeyboardButton(text="✅ Qualified", callback_data=f"qualify:{conversation.id}"),
                    InlineKeyboardButton(text="❌ Rejected", callback_data=f"reject:{conversation.id}"),
                ]
            ]
        )
        try:
            await self._send_with_retry(bot, chat_id=self._chat_id, text=text, reply_markup=kb)
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
    """
    await _service.send_meeting_booked_alert(contact, conversation)
