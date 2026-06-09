"""Tests for operator notification service."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

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
async def test_notify_operator_hot_lead_runs_without_error(dummy_contact, dummy_conversation):
    result = await notify_operator_hot_lead(dummy_contact, dummy_conversation)
    assert result is None


@pytest.mark.asyncio
async def test_notify_operator_meeting_booked_runs_without_error(dummy_contact, dummy_conversation):
    result = await notify_operator_meeting_booked(dummy_contact, dummy_conversation)
    assert result is None


class TestNotificationService:
    async def test_send_hot_lead_alert_without_chat_id_logs_warning(self, dummy_contact, dummy_conversation, caplog):
        service = NotificationService(chat_id="")
        with caplog.at_level("WARNING"):
            await service.send_hot_lead_alert(dummy_contact, dummy_conversation)
        assert "ADMIN_NOTIFICATION_CHAT_ID is not set" in caplog.text

    async def test_send_hot_lead_alert_without_bot_token_logs_warning(self, dummy_contact, dummy_conversation, caplog):
        service = NotificationService(chat_id="12345")
        with caplog.at_level("WARNING"):
            with patch("app.services.notification_service.settings") as mock_settings:
                mock_settings.admin_bot_token = ""
                await service.send_hot_lead_alert(dummy_contact, dummy_conversation)
        assert "ADMIN_BOT_TOKEN is not set" in caplog.text

    async def test_send_hot_lead_alert_sends_message(self, dummy_contact, dummy_conversation):
        mock_bot = AsyncMock()
        service = NotificationService(bot=mock_bot, chat_id="12345")
        await service.send_hot_lead_alert(dummy_contact, dummy_conversation, "Last msg")

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == "12345"
        assert "🔥 Hot Lead" in call_kwargs["text"]
        assert "Last msg" in call_kwargs["text"]
        assert call_kwargs["reply_markup"] is not None

    async def test_send_meeting_booked_alert_sends_message(self, dummy_contact, dummy_conversation):
        mock_bot = AsyncMock()
        service = NotificationService(bot=mock_bot, chat_id="12345")
        await service.send_meeting_booked_alert(dummy_contact, dummy_conversation)

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "📅 Meeting Booked" in call_kwargs["text"]
        assert call_kwargs["reply_markup"] is not None

    async def test_send_hot_lead_alert_handles_exception(self, dummy_contact, dummy_conversation, caplog):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Telegram error")
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with caplog.at_level("ERROR"):
            await service.send_hot_lead_alert(dummy_contact, dummy_conversation)
        assert "Failed to send hot lead alert" in caplog.text

    async def test_send_meeting_booked_alert_handles_exception(self, dummy_contact, dummy_conversation, caplog):
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Telegram error")
        service = NotificationService(bot=mock_bot, chat_id="12345")
        with caplog.at_level("ERROR"):
            await service.send_meeting_booked_alert(dummy_contact, dummy_conversation)
        assert "Failed to send meeting booked alert" in caplog.text
