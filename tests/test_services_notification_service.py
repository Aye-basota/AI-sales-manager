"""Tests for operator notification service."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.services.notification_service import (
    NotificationService,
    notify_operator_hot_lead,
    notify_operator_meeting_booked,
)


@pytest.fixture
def dummy_contact():
    return Contact(
        id=uuid.uuid4(),
        telegram_username="testuser",
        phone="+123",
        first_name="John",
        status="new",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def dummy_conversation():
    return Conversation(
        id=uuid.uuid4(),
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        current_state="hot",
        facts_extracted={},
        created_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_notify_operator_hot_lead_runs_without_error(
    dummy_contact, dummy_conversation
):
    result = await notify_operator_hot_lead(dummy_contact, dummy_conversation)
    assert result is None


@pytest.mark.asyncio
async def test_notify_operator_meeting_booked_runs_without_error(
    dummy_contact, dummy_conversation
):
    result = await notify_operator_meeting_booked(dummy_contact, dummy_conversation)
    assert result is None


class TestNotificationService:
    async def test_send_hot_lead_alert_without_chat_id_logs_warning(
        self, dummy_contact, dummy_conversation, caplog
    ):
        service = NotificationService(chat_id="")
        with caplog.at_level("WARNING"):
            await service.send_hot_lead_alert(dummy_contact, dummy_conversation)
        assert "ADMIN_NOTIFICATION_CHAT_ID is not set" in caplog.text

    async def test_send_hot_lead_alert_without_bot_token_logs_warning(
        self, dummy_contact, dummy_conversation, caplog
    ):
        service = NotificationService(chat_id="12345")
        with caplog.at_level("WARNING"):
            with patch("app.services.notification_service.settings") as mock_settings:
                mock_settings.admin_bot_token = ""
                await service.send_hot_lead_alert(dummy_contact, dummy_conversation)
        assert "ADMIN_BOT_TOKEN is not set" in caplog.text

    async def test_send_hot_lead_alert_sends_message(
        self, dummy_contact, dummy_conversation
    ):
        mock_bot = AsyncMock()
        service = NotificationService(bot=mock_bot, chat_id="12345")
        await service.send_hot_lead_alert(dummy_contact, dummy_conversation, "Last msg")

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == "12345"
        assert "🔥 Новый Hot Lead!" in call_kwargs["text"]
        assert "Last msg" in call_kwargs["text"]
        assert call_kwargs["reply_markup"] is not None

    async def test_send_meeting_booked_alert_sends_message(
        self, dummy_contact, dummy_conversation
    ):
        mock_bot = AsyncMock()
        service = NotificationService(bot=mock_bot, chat_id="12345")
        await service.send_meeting_booked_alert(dummy_contact, dummy_conversation)

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "📅 Meeting Booked\n" in call_kwargs["text"]
        assert call_kwargs["reply_markup"] is not None

    async def test_send_owner_clarification_request_sends_action_buttons(
        self, dummy_contact, dummy_conversation
    ):
        mock_bot = AsyncMock()
        service = NotificationService(bot=mock_bot, chat_id="12345")

        await service.send_owner_clarification_request(
            dummy_contact,
            dummy_conversation,
            category_label="цены",
            question="Какие цены можно называть?",
            lead_message_text="Сколько стоит 10000 штук?",
        )

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        callbacks = [
            button.callback_data
            for row in call_kwargs["reply_markup"].inline_keyboard
            for button in row
        ]
        assert "❓ Нужен ответ владельца" in call_kwargs["text"]
        assert "Сколько стоит 10000 штук?" in call_kwargs["text"]
        assert f"clarify:{dummy_conversation.id}" in callbacks
        assert f"dialog:{dummy_conversation.id}" in callbacks

    async def test_send_meeting_booked_alert_without_chat_id_logs_warning(
        self, dummy_contact, dummy_conversation, caplog
    ):
        service = NotificationService(chat_id="")
        with caplog.at_level("WARNING"):
            await service.send_meeting_booked_alert(dummy_contact, dummy_conversation)
        assert "ADMIN_NOTIFICATION_CHAT_ID is not set" in caplog.text

    async def test_send_meeting_booked_alert_without_bot_token_logs_warning(
        self, dummy_contact, dummy_conversation, caplog
    ):
        service = NotificationService(chat_id="12345")
        with caplog.at_level("WARNING"):
            with patch("app.services.notification_service.settings") as mock_settings:
                mock_settings.admin_bot_token = ""
                await service.send_meeting_booked_alert(
                    dummy_contact, dummy_conversation
                )
        assert "ADMIN_BOT_TOKEN is not set" in caplog.text

    async def test_send_hot_lead_alert_handles_exception(
        self, dummy_contact, dummy_conversation, caplog
    ):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Telegram error")
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with caplog.at_level("ERROR"):
            await service.send_hot_lead_alert(dummy_contact, dummy_conversation)
        assert "Failed to send hot lead alert" in caplog.text

    async def test_send_meeting_booked_alert_handles_exception(
        self, dummy_contact, dummy_conversation, caplog
    ):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Telegram error")
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with caplog.at_level("ERROR"):
            await service.send_meeting_booked_alert(dummy_contact, dummy_conversation)
        assert "Failed to send meeting booked alert" in caplog.text

    async def test_send_hot_lead_alert_retries_on_telegram_retry_after(
        self, dummy_contact, dummy_conversation
    ):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = [
            TelegramRetryAfter(
                method="send_message", message="Retry after", retry_after=1
            ),
            None,
        ]
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with patch("app.services.notification_service.asyncio.sleep") as mock_sleep:
            await service.send_hot_lead_alert(dummy_contact, dummy_conversation, "msg")
        assert mock_bot.send_message.await_count == 2
        mock_sleep.assert_awaited_once_with(1)

    async def test_send_hot_lead_alert_retries_on_telegram_api_error(
        self, dummy_contact, dummy_conversation
    ):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = [
            TelegramAPIError(method="send_message", message="API error"),
            None,
        ]
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with patch("app.services.notification_service.asyncio.sleep") as mock_sleep:
            await service.send_hot_lead_alert(dummy_contact, dummy_conversation, "msg")
        assert mock_bot.send_message.await_count == 2
        mock_sleep.assert_awaited_once_with(1)

    async def test_send_hot_lead_alert_exhausted_retries_on_retry_after(
        self, dummy_contact, dummy_conversation, caplog
    ):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = TelegramRetryAfter(
            method="send_message", message="Retry after", retry_after=2
        )
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with caplog.at_level("ERROR"):
            with patch("app.services.notification_service.asyncio.sleep") as mock_sleep:
                await service.send_hot_lead_alert(
                    dummy_contact, dummy_conversation, "msg"
                )
        assert mock_bot.send_message.await_count == 4  # initial + 3 retries
        assert mock_sleep.await_count == 3
        mock_sleep.assert_any_await(2)
        assert "Failed to send hot lead alert" in caplog.text

    async def test_send_meeting_booked_alert_exhausted_retries_on_api_error(
        self, dummy_contact, dummy_conversation, caplog
    ):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = TelegramAPIError(
            method="send_message", message="API error"
        )
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with caplog.at_level("ERROR"):
            with patch("app.services.notification_service.asyncio.sleep") as mock_sleep:
                await service.send_meeting_booked_alert(
                    dummy_contact, dummy_conversation
                )
        assert mock_bot.send_message.await_count == 4  # initial + 3 retries
        assert mock_sleep.await_count == 3
        mock_sleep.assert_any_await(1)
        mock_sleep.assert_any_await(2)
        mock_sleep.assert_any_await(4)
        assert "Failed to send meeting booked alert" in caplog.text
