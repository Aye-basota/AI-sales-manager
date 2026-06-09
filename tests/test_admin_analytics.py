"""Dedicated tests for Admin Bot analytics and hot leads commands."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import types

from app.bots.admin_bot import (
    cmd_analytics,
    cmd_hotleads,
    _format_analytics,
    _format_hotleads,
)
from app.models import Contact, Conversation


@pytest.fixture
def mock_message():
    msg = AsyncMock(spec=types.Message)
    msg.answer = AsyncMock()
    return msg


def _make_mock_session(result_mock):
    session = AsyncMock()
    session.execute.return_value = result_mock
    session.add = MagicMock()
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


class TestAnalyticsCommand:
    async def test_returns_correct_metrics(self, mock_message):
        session = AsyncMock()
        session.scalar.side_effect = [150, 142, 18, 3, 1]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_analytics(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Всего контактов: 150" in text
        assert "Отправлено: 142" in text
        assert "Ответили: 18 (12.7%)" in text
        assert "Hot leads: 3" in text
        assert "Встречи: 1" in text

    async def test_zero_division_handling(self, mock_message):
        session = AsyncMock()
        session.scalar.side_effect = [0, 0, 0, 0, 0]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_analytics(mock_message)

        text = mock_message.answer.call_args[0][0]
        assert "Ответили: 0 (0.0%)" in text


class TestHotleadsCommand:
    async def test_returns_formatted_hot_leads(self, mock_message):
        conv = Conversation(
            id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            current_state="hot",
            sentiment="positive",
        )
        contact = Contact(
            id=conv.contact_id,
            telegram_username="hotlead1",
            phone="",
            first_name="Alice",
            company_name="Acme",
        )
        result_mock = MagicMock()
        result_mock.all.return_value = [(conv, contact)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_hotleads(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "hotlead1" in text
        assert "State: hot" in text
        assert "Sentiment: positive" in text
        # Inline keyboard should contain qualify/reject/dialog buttons
        kb = mock_message.answer.call_args[1].get("reply_markup")
        assert kb is not None

    async def test_returns_meeting_booked(self, mock_message):
        conv = Conversation(
            id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            current_state="meeting_booked",
            sentiment=None,
        )
        contact = Contact(
            id=conv.contact_id,
            telegram_username=None,
            phone="+79990000000",
            first_name="Bob",
        )
        result_mock = MagicMock()
        result_mock.all.return_value = [(conv, contact)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_hotleads(mock_message)

        text = mock_message.answer.call_args[0][0]
        assert "+79990000000" in text
        assert "Sentiment: N/A" in text
        assert "📅" in text

    async def test_empty_hot_leads(self, mock_message):
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_hotleads(mock_message)

        mock_message.answer.assert_called_once_with("No hot leads or meetings booked.")


class TestFormatAnalytics:
    def test_format_with_various_numbers(self):
        text = _format_analytics(1000, 950, 120, 15, 8)
        assert "Всего контактов: 1000" in text
        assert "Отправлено: 950" in text
        assert "Ответили: 120 (12.6%)" in text
        assert "Hot leads: 15" in text
        assert "Встречи: 8" in text

    def test_format_rounds_reply_rate(self):
        text = _format_analytics(100, 50, 1, 0, 0)
        assert "Ответили: 1 (2.0%)" in text


class TestFormatHotleads:
    def test_hot_lead_formatting(self):
        conv = Conversation(id=uuid.uuid4(), current_state="hot", sentiment="positive")
        contact = Contact(id=uuid.uuid4(), telegram_username="@john", phone="")
        text = _format_hotleads([(conv, contact)])
        assert "@john" in text
        assert "State: hot" in text
        assert "🔥" in text

    def test_phone_fallback(self):
        conv = Conversation(id=uuid.uuid4(), current_state="meeting_booked", sentiment=None)
        contact = Contact(id=uuid.uuid4(), telegram_username=None, phone="+123")
        text = _format_hotleads([(conv, contact)])
        assert "+123" in text
        assert "📅" in text
