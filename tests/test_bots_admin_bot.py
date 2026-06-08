import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import types

from app.bots.admin_bot import (
    _format_scripts,
    _format_campaigns,
    _format_hotleads,
    cmd_start,
    cmd_scripts,
    cmd_campaigns,
    cmd_analytics,
    cmd_hotleads,
    start_bot,
    stop_bot,
)
from app.models import Script, Campaign, Conversation, Contact


@pytest.fixture
def mock_message():
    msg = AsyncMock(spec=types.Message)
    msg.answer = AsyncMock()
    return msg


class TestFormatScripts:
    def test_single_active_script(self):
        script = Script(
            id=uuid.uuid4(),
            name="Test Script",
            goal="Book demo",
            max_messages=3,
            tone="friendly",
            is_active=True,
        )
        text = _format_scripts([script])
        assert "Test Script" in text
        assert "Goal: Book demo" in text

    def test_inactive_script(self):
        script = Script(
            id=uuid.uuid4(),
            name="Inactive",
            goal="None",
            max_messages=1,
            tone="formal",
            is_active=False,
        )
        text = _format_scripts([script])
        assert "Inactive" in text


class TestFormatCampaigns:
    def test_single_campaign(self):
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Summer Sale",
            status="running",
            total_contacts=100,
            processed_contacts=50,
            replied_count=20,
            qualified_count=10,
            meeting_booked_count=2,
        )
        text = _format_campaigns([campaign])
        assert "Summer Sale" in text
        assert "Status: running" in text
        assert "Contacts: 50/100" in text


class TestFormatHotleads:
    def test_hot_lead(self):
        conv = Conversation(
            id=uuid.uuid4(),
            current_state="hot",
            sentiment="positive",
        )
        contact = Contact(
            id=uuid.uuid4(),
            telegram_username="@john",
            phone="",
        )
        text = _format_hotleads([(conv, contact)])
        assert "@john" in text
        assert "State: hot" in text

    def test_meeting_booked(self):
        conv = Conversation(
            id=uuid.uuid4(),
            current_state="meeting_booked",
            sentiment=None,
        )
        contact = Contact(
            id=uuid.uuid4(),
            telegram_username=None,
            phone="+79990000000",
        )
        text = _format_hotleads([(conv, contact)])
        assert "+79990000000" in text
        assert "Sentiment: N/A" in text


class TestCmdStart:
    async def test_sends_welcome(self, mock_message):
        await cmd_start(mock_message)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Welcome to AI Sales Manager Admin Bot" in text
        assert "/scripts" in text


def _make_mock_session(result_mock):
    session = AsyncMock()
    session.execute.return_value = result_mock
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


class TestCmdScripts:
    async def test_returns_formatted_scripts(self, mock_message):
        script = Script(
            id=uuid.uuid4(),
            name="Script A",
            goal="Greet",
            max_messages=1,
            tone="casual",
            is_active=True,
            created_at=datetime.now(),
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [script]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_scripts(mock_message)

        mock_message.answer.assert_called_once()
        assert "Script A" in mock_message.answer.call_args[0][0]

    async def test_empty_scripts(self, mock_message):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_scripts(mock_message)

        mock_message.answer.assert_called_once_with("No scripts found.")


class TestCmdCampaigns:
    async def test_returns_formatted_campaigns(self, mock_message):
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Campaign B",
            status="draft",
            total_contacts=10,
            processed_contacts=0,
            replied_count=0,
            qualified_count=0,
            meeting_booked_count=0,
            created_at=datetime.now(),
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [campaign]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_campaigns(mock_message)

        mock_message.answer.assert_called_once()
        assert "Campaign B" in mock_message.answer.call_args[0][0]


class TestCmdAnalytics:
    async def test_returns_metrics(self, mock_message):
        session = AsyncMock()
        session.scalar.side_effect = [5, 3, 100, 12]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_analytics(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Scripts: 5" in text
        assert "Campaigns: 3" in text
        assert "Hot leads / Meetings: 12" in text


class TestCmdHotleads:
    async def test_returns_hot_leads(self, mock_message):
        conv = Conversation(
            id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            current_state="hot",
            sentiment="positive",
        )
        contact = Contact(
            id=uuid.uuid4(),
            telegram_username="lead1",
            phone="",
        )
        result_mock = MagicMock()
        result_mock.all.return_value = [(conv, contact)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_hotleads(mock_message)

        mock_message.answer.assert_called_once()
        assert "lead1" in mock_message.answer.call_args[0][0]

    async def test_empty_hot_leads(self, mock_message):
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_hotleads(mock_message)

        mock_message.answer.assert_called_once_with("No hot leads or meetings booked.")


class TestStartBot:
    async def test_no_token_logs_warning(self, caplog):
        with patch("app.bots.admin_bot.settings") as mock_settings:
            mock_settings.admin_bot_token = ""
            with caplog.at_level("WARNING"):
                await start_bot()
            assert "ADMIN_BOT_TOKEN is not set" in caplog.text

    async def test_with_token_starts_polling(self):
        with patch("app.bots.admin_bot.settings") as mock_settings:
            mock_settings.admin_bot_token = "123456:ABC-DEF"
            mock_dp = AsyncMock()
            with patch("app.bots.admin_bot.dp", mock_dp):
                mock_bot = MagicMock()
                with patch("app.bots.admin_bot.Bot", return_value=mock_bot):
                    await start_bot()
                mock_dp.start_polling.assert_awaited_once()


class TestStopBot:
    async def test_closes_session(self):
        mock_bot_instance = AsyncMock()
        with patch.dict("app.bots.admin_bot.__dict__", {"_bot": mock_bot_instance}):
            await stop_bot()
        mock_bot_instance.session.close.assert_awaited_once()
