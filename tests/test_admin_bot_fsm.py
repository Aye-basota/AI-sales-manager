"""Dedicated tests for Admin Bot FSM transitions."""

import uuid
from datetime import time as dt_time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import types
from aiogram.fsm.context import FSMContext

from app.bots.admin_bot import (
    process_script_name,
    process_script_role,
    process_script_audience,
    process_script_goal,
    process_script_criteria,
    process_script_tone,
    process_script_first_message_goal,
    process_script_max_messages,
    process_script_delay,
    process_work_hours_default,
    process_work_hours_manual,
    process_script_timezone,
    confirm_create_script,
    cancel_create_script,
    cmd_upload,
    process_upload_file,
    start_campaign_from_csv,
    ScriptCreateFSM,
    CSVImportFSM,
    CampaignCreateFSM,
)
from app.models import Script


@pytest.fixture
def mock_message():
    msg = AsyncMock(spec=types.Message)
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_callback():
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.answer = AsyncMock()
    callback.message = AsyncMock(spec=types.Message)
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    return callback


@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    return state


def _make_mock_session(result_mock):
    session = AsyncMock()
    session.execute.return_value = result_mock
    session.add = MagicMock()
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


class TestNewScriptFSM:
    async def test_name_to_role_transition(self, mock_message, mock_state):
        mock_message.text = "Test Script"
        await process_script_name(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(name="Test Script")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.role_prompt)
        mock_message.answer.assert_called_once()

    async def test_role_to_audience_transition(self, mock_message, mock_state):
        mock_message.text = "Sales assistant"
        await process_script_role(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(role_prompt="Sales assistant")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.target_audience)

    async def test_audience_skip_to_goal(self, mock_message, mock_state):
        mock_message.text = "-"
        await process_script_audience(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(target_audience=None)
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.goal)

    async def test_goal_to_criteria_transition(self, mock_message, mock_state):
        mock_message.text = "Book a demo"
        await process_script_goal(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(goal="Book a demo")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.success_criteria)

    async def test_criteria_skip_to_tone(self, mock_message, mock_state):
        mock_message.text = "-"
        await process_script_criteria(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(success_criteria=None)
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.tone)

    async def test_tone_selection(self, mock_callback, mock_state):
        mock_callback.data = "tone:Деловой"
        await process_script_tone(mock_callback, mock_state)
        mock_state.update_data.assert_awaited_with(tone="professional")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.first_message_goal)
        mock_callback.message.answer.assert_called_once()
        mock_callback.answer.assert_awaited_once()

    async def test_first_message_goal_selection(self, mock_callback, mock_state):
        mock_callback.data = "fmg:hook"
        await process_script_first_message_goal(mock_callback, mock_state)
        mock_state.update_data.assert_awaited_with(first_message_goal="hook")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.call_to_action)

    async def test_max_messages_to_delay(self, mock_message, mock_state):
        mock_message.text = "3"
        await process_script_max_messages(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(max_messages=3)
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.follow_up_delay_hours)

    async def test_delay_to_work_hours(self, mock_message, mock_state):
        mock_message.text = "24"
        await process_script_delay(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(follow_up_delay_hours=24)
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.working_hours)

    async def test_work_hours_default_to_timezone(self, mock_callback, mock_state):
        await process_work_hours_default(mock_callback, mock_state)
        mock_state.update_data.assert_any_await(working_hours_start=dt_time(9, 0))
        mock_state.update_data.assert_any_await(working_hours_end=dt_time(18, 0))
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.timezone)
        mock_callback.answer.assert_awaited_once()

    async def test_work_hours_manual_prompts_input(self, mock_callback, mock_state):
        await process_work_hours_manual(mock_callback, mock_state)
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.working_hours)
        mock_callback.answer.assert_awaited_once()

    async def test_timezone_to_confirm(self, mock_message, mock_state):
        mock_state.get_data.return_value = {
            "name": "Test",
            "role_prompt": "Role",
            "target_audience": None,
            "goal": "Goal",
            "success_criteria": None,
            "tone": "professional",
            "max_messages": 2,
            "follow_up_delay_hours": 24,
            "working_hours_start": dt_time(9, 0),
            "working_hours_end": dt_time(18, 0),
        }
        mock_message.text = "Europe/Moscow"
        await process_script_timezone(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(timezone="Europe/Moscow")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.confirm)
        assert "Проверьте данные" in mock_message.answer.call_args[0][0]

    async def test_confirm_creates_script(self, mock_callback, mock_state):
        mock_state.get_data.return_value = {
            "name": "Test Script",
            "role_prompt": "Role",
            "target_audience": None,
            "goal": "Goal",
            "success_criteria": None,
            "tone": "professional",
            "first_message_goal": "hook",
            "call_to_action": "15-минутный созвон",
            "language": "ru",
            "emoji_policy": "forbidden",
            "max_first_message_length": 200,
            "max_messages": 2,
            "follow_up_delay_hours": 24,
            "working_hours_start": dt_time(9, 0),
            "working_hours_end": dt_time(18, 0),
            "timezone": "Europe/Moscow",
        }
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await confirm_create_script(mock_callback, mock_state)

        mock_state.clear.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("✅ Скрипт создан!")

    async def test_cancel_clears_state(self, mock_callback, mock_state):
        await cancel_create_script(mock_callback, mock_state)
        mock_state.clear.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("❌ Создание отменено")


class TestUploadFSM:
    async def test_upload_requests_file(self, mock_message, mock_state):
        await cmd_upload(mock_message, mock_state)
        mock_state.set_state.assert_awaited_with(CSVImportFSM.waiting_file)
        text = mock_message.answer.call_args[0][0]
        assert "CSV" in text
        assert "Excel" in text
        assert "/cancel" in text
        assert mock_message.answer.call_args.kwargs.get("reply_markup") is not None

    async def test_rejects_non_document(self, mock_message, mock_state):
        mock_message.document = None
        await process_upload_file(mock_message, mock_state)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Пожалуйста, отправьте файл" in text
        assert "/cancel" in text
        assert mock_message.answer.call_args.kwargs.get("reply_markup") is not None

    async def test_rejects_unsupported_extension(self, mock_message, mock_state):
        mock_message.document = MagicMock()
        mock_message.document.file_name = "file.txt"
        await process_upload_file(mock_message, mock_state)
        mock_message.answer.assert_called_once_with(
            "❌ Принимаются только CSV и Excel файлы."
        )

    async def test_upload_transitions_to_preview(self, mock_message, mock_state):
        mock_message.document = MagicMock()
        mock_message.document.file_name = "contacts.csv"
        mock_message.document.file_id = "file123"

        file_bytes = MagicMock()
        file_bytes.read.return_value = (
            b"first_name,last_name,telegram_user_id\nAlice,Smith,123456"
        )

        mock_bot = AsyncMock()
        mock_bot.get_file = AsyncMock(return_value=MagicMock(file_path="path"))
        mock_bot.download_file = AsyncMock(return_value=file_bytes)

        with patch("app.bots.admin_bot._get_bot", return_value=mock_bot):
            await process_upload_file(mock_message, mock_state)

        mock_state.update_data.assert_awaited()
        mock_state.set_state.assert_awaited_with(CSVImportFSM.preview)
        text = mock_message.answer.call_args[0][0]
        assert "Найдено" in text

    async def test_campaign_creation_from_upload(self, mock_callback, mock_state):
        mock_state.get_data.return_value = {
            "records": [
                {"first_name": "Alice", "telegram_username": "alice"},
            ],
        }

        script = Script(
            id=uuid.uuid4(),
            name="Test Script",
            goal="Book",
            max_messages=2,
            tone="professional",
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [script]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await start_campaign_from_csv(mock_callback, mock_state)

        mock_state.set_state.assert_awaited_with(CampaignCreateFSM.select_script)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.message.answer.assert_not_awaited()
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Выберите скрипт" in text
