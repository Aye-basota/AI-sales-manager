import asyncio
import logging
import uuid
import re
from datetime import datetime, time as dt_time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from app.bots.admin_bot import (
    _format_scripts,
    _format_campaigns,
    _format_hotleads,
    _format_analytics,
    _build_campaign_buttons,
    _build_script_buttons,
    _dispatch_navigation_override,
    _main_menu_keyboard,
    _notify_admin_error,
    _send_or_edit_scripts,
    _send_or_edit_campaigns,
    handle_script_view,
    handle_script_edit_field,
    process_script_edit_value,
    _generate_preview_message,
    CallbackStateGuardMiddleware,
    cmd_start,
    cmd_help,
    cmd_cancel,
    cmd_scripts,
    cmd_campaigns,
    cmd_analytics,
    cmd_hotleads,
    cmd_conversations,
    handle_qualify,
    handle_reject,
    handle_dialog,
    handle_history,
    start_bot,
    stop_bot,
    cmd_newscript,
    process_script_name,
    process_script_role,
    process_script_audience,
    process_script_goal,
    process_script_criteria,
    process_script_tone,
    process_script_strategy,
    process_script_max_messages,
    process_script_delay,
    process_script_timezone,
    confirm_create_script,
    cancel_create_script,
    cmd_upload,
    process_upload_file,
    cmd_startcampaign,
    handle_startcamp,
    handle_camp_start,
    handle_camp_pause,
    handle_camp_resume,
    handle_camp_delete,
    process_work_hours_default,
    process_work_hours_manual,
    process_campaign_script,
    handle_preview_regenerate,
    handle_preview_change_script,
    handle_preview_launch,
    cancel_campaign_script_selection,
    handle_script_delete,
    handle_script_toggle,
    handle_menu_button,
    handle_unknown_callback,
    handle_unknown_message,
    _set_admin_bot_commands,
    handle_language_choice,
    _admin_language_by_user,
    LANG_EN,
    MENU_ANALYTICS,
    MENU_CAMPAIGNS,
    MENU_CONVERSATIONS,
    MENU_DISCOVER,
    MENU_HOT_LEADS,
    MENU_HANDLERS,
    MENU_NEW_SCRIPT,
    MENU_SCRIPTS,
    MENU_START_CAMPAIGN,
    MENU_UPLOAD,
    ScriptCreateFSM,
    ScriptEditFSM,
    CSVImportFSM,
    CampaignStartFSM,
    CampaignCreateFSM,
)
from app.models import Script, Campaign, Conversation, Contact, Message


@pytest.fixture
def mock_message():
    msg = AsyncMock(spec=types.Message)
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.is_bot = False
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
        assert "Цель: Book demo" in text

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

    def test_script_list_stays_compact_for_telegram_limit(self):
        scripts = []
        for idx in range(10):
            script = Script(
                id=uuid.uuid4(),
                name=f"Long Business {idx}",
                role_prompt="Long description " * 80,
                target_audience="Coffee shop owners " * 40,
                goal="Book a short call " * 40,
                max_messages=3,
                tone="friendly",
                is_active=True,
            )
            scripts.append((script, idx))

        text = _format_scripts(scripts)

        assert len(text) < 4096
        assert "Long description" not in text

    def test_script_list_english_is_fully_english(self):
        script = Script(
            id=uuid.uuid4(),
            name="Cups",
            goal="Book a call",
            target_audience="Coffee shops",
            is_active=True,
        )
        text = _format_scripts([script], LANG_EN)
        assert "Businesses" in text
        assert "Goal:" in text
        assert "Запусков" not in text


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
        assert "Статус: идет отправка" in text
        assert "Контакты: 50/100" in text

    def test_campaigns_english_labels(self):
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Summer Sale",
            status="draft",
            total_contacts=100,
            processed_contacts=0,
            replied_count=0,
            qualified_count=0,
            meeting_booked_count=0,
        )
        text = _format_campaigns([campaign], LANG_EN)
        assert "Business:" in text
        assert "Status: draft" in text
        assert "Контакты" not in text


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
        assert "Статус: готов к передаче" in text

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
        assert "созвон согласован" in text
        assert "Настроение: не определено" in text


class TestFormatAnalytics:
    def test_analytics_output(self):
        text = _format_analytics(150, 142, 18, 3, 1, 2, 120.7)
        assert "Всего контактов: 150" in text
        assert "Отправлено: 142" in text
        assert "Ответили: 18 (12.7%)" in text
        assert "Горячие лиды: 3" in text
        assert "Встречи: 1" in text
        assert "Guardrails отказов: 2" in text
        assert "Средняя длина сообщения: 121 симв." in text

    def test_analytics_english_output(self):
        text = _format_analytics(150, 142, 18, 3, 1, 2, 120.7, LANG_EN)
        assert "Total contacts: 150" in text
        assert "Replied: 18 (12.7%)" in text
        assert "Guardrail fallbacks: 2" in text
        assert "Всего" not in text


@pytest.mark.asyncio
async def test_admin_bot_command_registration_retries_timeout_without_traceback(monkeypatch, caplog):
    from app.bots import admin_bot

    calls = 0
    bot = AsyncMock()

    async def set_my_commands(_commands):
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(1)
        return True

    bot.set_my_commands = AsyncMock(side_effect=set_my_commands)
    monkeypatch.setattr(admin_bot, "COMMAND_REGISTRATION_ATTEMPTS", 2)
    monkeypatch.setattr(admin_bot, "COMMAND_REGISTRATION_TIMEOUT_S", 0.001)
    monkeypatch.setattr(admin_bot, "COMMAND_REGISTRATION_RETRY_DELAY_S", 0)
    caplog.set_level(logging.WARNING)

    result = await _set_admin_bot_commands(bot)

    assert result is True
    assert bot.set_my_commands.await_count == 2
    assert "TimeoutError" in caplog.text
    assert "Traceback" not in caplog.text


class TestCmdStart:
    async def test_sends_language_choice_first(self, mock_message):
        await cmd_start(mock_message)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Выберите язык" in text
        assert "Choose interface language" in text
        keyboard = mock_message.answer.call_args.kwargs.get("reply_markup")
        assert keyboard is not None
        assert keyboard.inline_keyboard[0][0].text == "Русский"

    async def test_language_choice_sends_english_menu(self, mock_callback):
        user_id = 12345
        mock_callback.from_user = MagicMock(id=user_id)
        mock_callback.data = "lang:en"

        await handle_language_choice(mock_callback)

        assert _admin_language_by_user[user_id] == "en"
        mock_callback.message.edit_text.assert_awaited_once_with("Language: English")
        mock_callback.message.answer.assert_awaited_once()
        text = mock_callback.message.answer.call_args[0][0]
        assert "Ready" in text
        keyboard = mock_callback.message.answer.call_args.kwargs["reply_markup"]
        labels = {button.text for row in keyboard.keyboard for button in row}
        assert "🧭 Businesses" in labels
        assert "👥 Contacts & launch" in labels

    async def test_main_menu_exposes_core_actions(self):
        keyboard = _main_menu_keyboard()
        labels = {
            button.text
            for row in keyboard.keyboard
            for button in row
        }
        assert MENU_NEW_SCRIPT in labels
        assert MENU_START_CAMPAIGN in labels
        assert MENU_DISCOVER in labels
        assert MENU_CONVERSATIONS in labels
        assert MENU_SCRIPTS in labels
        assert MENU_UPLOAD in labels
        assert MENU_CAMPAIGNS in labels
        assert MENU_HOT_LEADS in labels
        assert MENU_ANALYTICS in labels


class TestCmdHelp:
    async def test_shows_schema_and_commands(self, mock_message):
        await cmd_help(mock_message)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Бизнес отвечает" in text
        assert "Запуск связывает" in text
        assert "/scripts" in text
        assert "/upload" in text
        assert "/back" in text
        assert "/cancel" in text
        commands = re.findall(r"^(/[a-z]+)", text, flags=re.MULTILINE)
        assert len(commands) == len(set(commands))


class TestCmdCancel:
    async def test_no_active_state_returns_menu(self, mock_message, mock_state):
        mock_state.get_state.return_value = None
        await cmd_cancel(mock_message, mock_state)
        mock_state.clear.assert_not_awaited()
        mock_message.answer.assert_called_once()
        assert "Активного мастера нет" in mock_message.answer.call_args[0][0]
        assert mock_message.answer.call_args.kwargs.get("reply_markup") is not None

    async def test_active_state_is_cleared(self, mock_message, mock_state):
        mock_state.get_state.return_value = "ScriptCreateFSM:name"
        await cmd_cancel(mock_message, mock_state)
        mock_state.clear.assert_awaited_once()
        mock_message.answer.assert_called_once()
        assert "остановил текущий мастер" in mock_message.answer.call_args[0][0]


class TestAdminFallbacks:
    async def test_unknown_message_without_state_returns_helpful_reply(
        self, mock_message, mock_state
    ):
        mock_state.get_state.return_value = None
        await handle_unknown_message(mock_message, mock_state)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Не понял команду" in text
        assert "бизнес" in text.lower()
        assert mock_message.answer.call_args.kwargs.get("reply_markup") is not None

    async def test_unknown_message_inside_wizard_points_to_cancel(
        self, mock_message, mock_state
    ):
        mock_state.get_state.return_value = "CampaignCreateFSM:name"
        await handle_unknown_message(mock_message, mock_state)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "открыт мастер" in text
        assert "/cancel" in text

    async def test_unknown_callback_is_answered(self, mock_callback):
        mock_callback.data = "stale:button"
        await handle_unknown_callback(mock_callback)
        mock_callback.answer.assert_awaited_once_with(
            "Не понял кнопку. Откройте /start или /help.", show_alert=True
        )
        mock_callback.message.answer.assert_awaited_once()

    async def test_global_error_notifies_message_user(self, mock_message):
        update = SimpleNamespace(message=mock_message, edited_message=None)
        notified = await _notify_admin_error(update)
        assert notified is True
        mock_message.answer.assert_called_once()
        assert "бот не упал молча" in mock_message.answer.call_args[0][0]

    async def test_menu_button_routes_russian_stateful_action(self, mock_message, mock_state):
        handler = AsyncMock()
        original = MENU_HANDLERS[MENU_UPLOAD]
        MENU_HANDLERS[MENU_UPLOAD] = handler
        mock_message.text = MENU_UPLOAD
        try:
            await handle_menu_button(mock_message, mock_state)
        finally:
            MENU_HANDLERS[MENU_UPLOAD] = original

        handler.assert_awaited_once_with(mock_message, mock_state)

    async def test_menu_button_keeps_legacy_english_action(self, mock_message, mock_state):
        handler = AsyncMock()
        original = MENU_HANDLERS["Scripts"]
        MENU_HANDLERS["Scripts"] = handler
        mock_message.text = "Scripts"
        try:
            await handle_menu_button(mock_message, mock_state)
        finally:
            MENU_HANDLERS["Scripts"] = original

        handler.assert_awaited_once_with(mock_message)

    async def test_command_inside_wizard_switches_function(self, mock_message, mock_state):
        mock_message.text = "/scripts"
        mock_state.get_state.return_value = "CSVImportFSM:waiting_file"
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            handled = await _dispatch_navigation_override(mock_message, mock_state)

        assert handled is True
        mock_state.clear.assert_awaited_once()
        mock_message.answer.assert_called_once()
        assert "Бизнесов пока нет" in mock_message.answer.call_args[0][0]

    async def test_menu_inside_wizard_switches_function(self, mock_message, mock_state):
        mock_message.text = MENU_SCRIPTS
        mock_state.get_state.return_value = "CSVImportFSM:waiting_file"
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            handled = await _dispatch_navigation_override(mock_message, mock_state)

        assert handled is True
        mock_state.clear.assert_awaited_once()
        assert "Бизнесов пока нет" in mock_message.answer.call_args[0][0]

    async def test_unknown_command_inside_wizard_is_not_saved_as_answer(
        self, mock_message, mock_state
    ):
        mock_message.text = "/wrong"
        mock_state.get_state.return_value = "ScriptCreateFSM:name"

        handled = await _dispatch_navigation_override(mock_message, mock_state)

        assert handled is True
        mock_state.clear.assert_not_awaited()
        mock_message.answer.assert_called_once()
        assert "не будет записана как ответ" in mock_message.answer.call_args[0][0]

    async def test_stale_callback_is_blocked_before_handler(
        self, mock_callback, mock_state
    ):
        middleware = CallbackStateGuardMiddleware()
        handler = AsyncMock()
        mock_callback.data = "preview:launch"
        mock_state.get_state.return_value = "CSVImportFSM:waiting_file"

        result = await middleware(handler, mock_callback, {"state": mock_state})

        assert result is None
        handler.assert_not_awaited()
        mock_callback.answer.assert_awaited_once()
        assert mock_callback.answer.call_args.kwargs["show_alert"] is True
        mock_callback.message.answer.assert_awaited_once()


class TestCmdScripts:
    def test_script_keyboard_exposes_create_toggle_delete(self):
        script = Script(
            id=uuid.uuid4(),
            name="Script A",
            goal="Greet",
            max_messages=1,
            tone="casual",
            is_active=True,
        )

        keyboard = _build_script_buttons([(script, 0)])
        buttons = [button for row in keyboard.inline_keyboard for button in row]
        callbacks = [button.callback_data for button in buttons]

        assert "script_new" in callbacks
        assert any(callback.startswith("scriptv:") for callback in callbacks)
        assert any(callback.startswith("scripte:") for callback in callbacks)
        assert any(callback.startswith("script_toggle:") for callback in callbacks)
        assert any(callback.startswith("script_delete:") for callback in callbacks)

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
        result_mock.all.return_value = [(script, 2)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_scripts(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Script A" in text
        assert "Запусков с этим бизнесом: 2" in text

    async def test_empty_scripts(self, mock_message):
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_scripts(mock_message)

        mock_message.answer.assert_called_once()
        assert "Бизнесов пока нет" in mock_message.answer.call_args[0][0]
        assert mock_message.answer.call_args.kwargs.get("reply_markup") is not None

    async def test_edits_bot_message_for_callback_refresh(self, mock_message):
        script = Script(
            id=uuid.uuid4(),
            name="Script A",
            goal="Greet",
            max_messages=1,
            tone="casual",
            is_active=True,
            created_at=datetime.now(),
        )
        mock_message.from_user.is_bot = True
        result_mock = MagicMock()
        result_mock.all.return_value = [(script, 0)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await _send_or_edit_scripts(mock_message)

        mock_message.edit_text.assert_awaited_once()
        mock_message.answer.assert_not_called()

    async def test_script_toggle_flips_active_status(self, mock_callback):
        script = Script(
            id=uuid.uuid4(),
            name="Script A",
            goal="Greet",
            is_active=True,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = script
        context = _make_mock_session(result_mock)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot.cmd_scripts", new=AsyncMock()) as mock_scripts,
        ):
            mock_callback.data = f"script_toggle:{script.id}"
            await handle_script_toggle(mock_callback)

        assert script.is_active is False
        mock_callback.answer.assert_awaited_once_with("✅ Обновлено")
        mock_scripts.assert_awaited_once_with(mock_callback.message)

    async def test_script_delete_rejects_malformed_id(self, mock_callback):
        mock_callback.data = "script_delete:not-a-uuid:0"

        with patch("app.bots.admin_bot.AsyncSessionLocal") as mock_session:
            await handle_script_delete(mock_callback)

        mock_session.assert_not_called()
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

    async def test_script_delete_blocks_scripts_used_by_campaigns(self, mock_callback):
        script_id = uuid.uuid4()
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        session = AsyncMock()
        session.execute.return_value = count_result
        session.delete = AsyncMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            mock_callback.data = f"script_delete:{script_id}:2"
            await handle_script_delete(mock_callback)

        session.delete.assert_not_awaited()
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес используется в запусках")

    async def test_script_delete_removes_unused_script(self, mock_callback):
        script = Script(id=uuid.uuid4(), name="Unused", goal="Greet", is_active=True)
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = script
        session = AsyncMock()
        session.execute.side_effect = [count_result, script_result]
        session.delete = AsyncMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot.cmd_scripts", new=AsyncMock()) as mock_scripts,
        ):
            mock_callback.data = f"script_delete:{script.id}:0"
            await handle_script_delete(mock_callback)

        session.delete.assert_awaited_once_with(script)
        session.commit.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("🗑 Бизнес удален")
        mock_scripts.assert_awaited_once_with(mock_callback.message)

    async def test_script_view_shows_business_details(self, mock_callback):
        script = Script(
            id=uuid.uuid4(),
            name="Стаканчики",
            role_prompt="Поставляем бумажные стаканчики для кофеен.",
            target_audience="Кофейни",
            goal="Предложить образцы",
            success_criteria="Лид попросил каталог",
            tone="friendly",
            is_active=True,
        )
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = script
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        session = AsyncMock()
        session.execute.side_effect = [script_result, count_result]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        mock_callback.data = f"scriptv:{script.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_script_view(mock_callback)

        mock_callback.message.edit_text.assert_awaited_once()
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Стаканчики" in text
        assert "Поставляем бумажные стаканчики" in text
        assert "Кофейни" in text

    async def test_script_edit_field_sets_value_state(self, mock_callback, mock_state):
        script = Script(id=uuid.uuid4(), name="Biz", role_prompt="Old", goal="Goal")
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = script
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        session = AsyncMock()
        session.execute.side_effect = [script_result, count_result]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        mock_callback.data = f"scriptf:role:{script.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_script_edit_field(mock_callback, mock_state)

        mock_state.set_state.assert_awaited_with(ScriptEditFSM.value)
        mock_state.update_data.assert_awaited_with(
            edit_script_id=str(script.id), edit_field="role_prompt"
        )
        assert "Описание бизнеса" in mock_callback.message.edit_text.call_args[0][0]

    async def test_script_edit_value_updates_timezone_strictly(
        self, mock_message, mock_state
    ):
        script = Script(id=uuid.uuid4(), name="Biz", role_prompt="Role", goal="Goal")
        mock_state.get_data.return_value = {
            "edit_script_id": str(script.id),
            "edit_field": "timezone",
        }
        mock_message.text = "msk"
        result = MagicMock()
        result.scalar_one_or_none.return_value = script
        context = _make_mock_session(result)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await process_script_edit_value(mock_message, mock_state)

        assert script.timezone == "Europe/Moscow"
        mock_state.clear.assert_awaited_once()
        assert "Сохранил" in mock_message.answer.call_args[0][0]

    async def test_script_edit_value_rejects_unknown_timezone(
        self, mock_message, mock_state
    ):
        mock_state.get_data.return_value = {
            "edit_script_id": str(uuid.uuid4()),
            "edit_field": "timezone",
        }
        mock_message.text = "mop"

        await process_script_edit_value(mock_message, mock_state)

        mock_message.answer.assert_called_once()
        assert "Не понял часовой пояс" in mock_message.answer.call_args[0][0]


class TestCmdCampaigns:
    async def test_returns_formatted_campaigns(self, mock_message):
        script = Script(
            id=uuid.uuid4(),
            name="Script B",
            goal="Book",
            max_messages=2,
            tone="professional",
        )
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
        result_mock.all.return_value = [(campaign, script)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_campaigns(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Campaign B" in text
        assert "Бизнес: Script B" in text
        assert "Контакты: 0/10" in text
        assert "Ответили: 0" in text


class TestCmdAnalytics:
    async def test_returns_metrics(self, mock_message):
        session = AsyncMock()
        session.scalar.side_effect = [150, 142, 18, 3, 1, 2, 120.5]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_analytics(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Всего контактов: 150" in text
        assert "Ответили: 18 (12.7%)" in text


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

        mock_message.answer.assert_called_once()
        assert "Горячих лидов пока нет" in mock_message.answer.call_args[0][0]


class TestStartBot:
    async def test_no_token_logs_warning(self, caplog):
        with patch("app.bots.admin_bot.settings") as mock_settings:
            mock_settings.admin_bot_token = ""
            with caplog.at_level("WARNING"):
                await start_bot()
            assert "ADMIN_BOT_TOKEN is not configured" in caplog.text

    async def test_placeholder_token_does_not_start_polling(self, caplog):
        with patch("app.bots.admin_bot.settings") as mock_settings:
            mock_settings.admin_bot_token = "your_telegram_bot_token"
            mock_dp = AsyncMock()
            with patch("app.bots.admin_bot.dp", mock_dp):
                with caplog.at_level("WARNING"):
                    await start_bot()
            mock_dp.start_polling.assert_not_awaited()
            assert "ADMIN_BOT_TOKEN is not configured" in caplog.text

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


class TestCmdConversations:
    async def test_missing_args_shows_recent_dialogs_help_when_empty(self, mock_message):
        mock_message.text = "/conversations"
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once()
        assert "Диалогов пока нет" in mock_message.answer.call_args[0][0]

    async def test_menu_label_shows_recent_dialogs_instead_of_searching(self, mock_message):
        from app.bots.admin_bot import MENU_CONVERSATIONS

        mock_message.text = MENU_CONVERSATIONS
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once()
        assert "Не нашел диалог" not in mock_message.answer.call_args[0][0]
        assert "Диалогов пока нет" in mock_message.answer.call_args[0][0]

    async def test_missing_args_shows_recent_dialogs(self, mock_message):
        contact = Contact(
            id=uuid.uuid4(),
            telegram_username="lead1",
            first_name="Lead",
            last_name="One",
        )
        conv = Conversation(
            id=uuid.uuid4(),
            contact_id=contact.id,
            current_state="hot",
            last_message_at=datetime.now(),
        )
        mock_message.text = "/conversations"
        result_mock = MagicMock()
        result_mock.all.return_value = [(conv, contact)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Последние диалоги" in text
        assert "lead1" in text
        assert mock_message.answer.call_args.kwargs.get("reply_markup") is not None

    async def test_legacy_usage_text_removed(self, mock_message):
        mock_message.text = "/conversations"
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once()
        assert "Usage:" not in mock_message.answer.call_args[0][0]

    async def test_invalid_uuid(self, mock_message):
        mock_message.text = "/conversations invalid"
        with patch(
            "app.bots.admin_bot._find_conversation_id_by_query",
            new=AsyncMock(return_value=None),
        ):
            await cmd_conversations(mock_message)
        mock_message.answer.assert_called_once()
        assert "Не нашел диалог" in mock_message.answer.call_args[0][0]
        assert "@username" in mock_message.answer.call_args[0][0]

    async def test_conversation_not_found(self, mock_message):
        mock_message.text = f"/conversations {uuid.uuid4()}"
        with patch(
            "app.bots.admin_bot._find_conversation_id_by_query",
            new=AsyncMock(return_value=None),
        ):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once()
        assert "Не нашел диалог" in mock_message.answer.call_args[0][0]

    async def test_returns_messages(self, mock_message):
        contact_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        mock_message.text = f"/conversations {contact_id}"

        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            direction="inbound",
            content="Hello",
        )

        with (
            patch(
                "app.bots.admin_bot._find_conversation_id_by_query",
                new=AsyncMock(return_value=conv_id),
            ),
            patch(
                "app.bots.admin_bot._load_conversation_messages",
                new=AsyncMock(return_value=[msg]),
            ),
        ):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Hello" in text

    async def test_no_messages(self, mock_message):
        contact_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        mock_message.text = f"/conversations {contact_id}"

        with (
            patch(
                "app.bots.admin_bot._find_conversation_id_by_query",
                new=AsyncMock(return_value=conv_id),
            ),
            patch(
                "app.bots.admin_bot._load_conversation_messages",
                new=AsyncMock(return_value=[]),
            ),
        ):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once_with("В диалоге пока нет сообщений.")


class TestHandleQualify:
    async def test_qualifies_conversation(self, mock_callback):
        conv = Conversation(id=uuid.uuid4(), current_state="hot")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = conv
        context = _make_mock_session(result_mock)

        mock_callback.data = f"qualify:{conv.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_qualify(mock_callback)

        assert conv.operator_status == "qualified"
        mock_callback.answer.assert_awaited_once_with("✅ Отмечено: готов к работе")

    async def test_conversation_not_found(self, mock_callback):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        context = _make_mock_session(result_mock)

        mock_callback.data = f"qualify:{uuid.uuid4()}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_qualify(mock_callback)

        mock_callback.answer.assert_awaited_once_with("❌ Диалог не найден")

    async def test_invalid_uuid(self, mock_callback):
        mock_callback.data = "qualify:invalid"
        await handle_qualify(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID диалога")


class TestHandleReject:
    async def test_rejects_conversation(self, mock_callback):
        conv = Conversation(id=uuid.uuid4(), current_state="hot")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = conv
        context = _make_mock_session(result_mock)

        mock_callback.data = f"reject:{conv.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_reject(mock_callback)

        assert conv.operator_status == "rejected"
        mock_callback.answer.assert_awaited_once_with("🚫 Отмечено: не целевой")

    async def test_conversation_not_found(self, mock_callback):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        context = _make_mock_session(result_mock)

        mock_callback.data = f"reject:{uuid.uuid4()}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_reject(mock_callback)

        mock_callback.answer.assert_awaited_once_with("❌ Диалог не найден")

    async def test_invalid_uuid(self, mock_callback):
        mock_callback.data = "reject:invalid"
        await handle_reject(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID диалога")


class TestHandleDialog:
    async def test_shows_last_10_messages(self, mock_callback):
        conv_id = uuid.uuid4()
        msg1 = Message(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            direction="outbound",
            content="Hello",
        )
        msg2 = Message(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            direction="inbound",
            content="Hi there",
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [msg2, msg1]
        context = _make_mock_session(result_mock)

        mock_callback.data = f"dialog:{conv_id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_dialog(mock_callback)

        mock_callback.message.answer.assert_called_once()
        text = mock_callback.message.answer.call_args[0][0]
        assert "🤖 Hello" in text
        assert "👤 Hi there" in text
        mock_callback.answer.assert_awaited_once()

    async def test_no_messages(self, mock_callback):
        conv_id = uuid.uuid4()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        context = _make_mock_session(result_mock)

        mock_callback.data = f"dialog:{conv_id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_dialog(mock_callback)

        mock_callback.message.answer.assert_called_once_with(
            "Сообщений в диалоге не найдено."
        )
        mock_callback.answer.assert_awaited_once()

    async def test_invalid_uuid(self, mock_callback):
        mock_callback.data = "dialog:invalid"
        await handle_dialog(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID диалога")


class TestHandleHistory:
    async def test_shows_last_20_messages_with_timestamps(self, mock_callback):
        conv_id = uuid.uuid4()
        msg1 = Message(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            direction="outbound",
            content="Hello",
            sent_at=datetime(2024, 1, 1, 10, 30),
        )
        msg2 = Message(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            direction="inbound",
            content="Hi there",
            sent_at=datetime(2024, 1, 1, 10, 31),
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [msg2, msg1]
        context = _make_mock_session(result_mock)

        mock_callback.data = f"history:{conv_id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_history(mock_callback)

        mock_callback.message.answer.assert_called()
        text = mock_callback.message.answer.call_args[0][0]
        assert "🤖" in text
        assert "👤" in text
        assert "10:30 01.01" in text
        assert "Hello" in text
        mock_callback.answer.assert_awaited_once()

    async def test_no_messages(self, mock_callback):
        conv_id = uuid.uuid4()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        context = _make_mock_session(result_mock)

        mock_callback.data = f"history:{conv_id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_history(mock_callback)

        mock_callback.message.answer.assert_called_once_with(
            "Сообщений в диалоге не найдено."
        )
        mock_callback.answer.assert_awaited_once()

    async def test_invalid_uuid(self, mock_callback):
        mock_callback.data = "history:invalid"
        await handle_history(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID диалога")


# ---------------------------------------------------------------------------
# FSM Tests
# ---------------------------------------------------------------------------


class TestCmdNewScript:
    async def test_starts_dialog(self, mock_message, mock_state):
        await cmd_newscript(mock_message, mock_state)
        mock_state.set_state.assert_awaited_once_with(ScriptCreateFSM.name)
        mock_message.answer.assert_called_once()
        assert "бизнес" in mock_message.answer.call_args[0][0].lower()


class TestProcessScriptFSM:
    async def test_name_to_role_prompt(self, mock_message, mock_state):
        mock_message.text = "Test Script"
        await process_script_name(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(name="Test Script")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.role_prompt)
        mock_message.answer.assert_called_once()

    async def test_role_to_audience(self, mock_message, mock_state):
        mock_message.text = "Role prompt"
        await process_script_role(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(role_prompt="Role prompt")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.target_audience)

    async def test_audience_skipped(self, mock_message, mock_state):
        mock_message.text = "-"
        await process_script_audience(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(target_audience=None)

    async def test_goal_to_criteria(self, mock_message, mock_state):
        mock_message.text = "Goal"
        await process_script_goal(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(goal="Goal")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.success_criteria)

    async def test_criteria_skipped(self, mock_message, mock_state):
        mock_message.text = "-"
        await process_script_criteria(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(success_criteria=None)

    async def test_tone_callback(self, mock_callback, mock_state):
        mock_callback.data = "tone:Деловой"
        await process_script_tone(mock_callback, mock_state)
        mock_state.update_data.assert_awaited_with(
            tone="professional",
            first_message_goal="trust",
            language="ru",
            emoji_policy="forbidden",
            max_first_message_length=240,
            max_messages=3,
        )
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.sales_strategy)

    async def test_strategy_callback_sets_real_sales_funnel(self, mock_callback, mock_state):
        mock_callback.data = "strategy:quick_call"
        await process_script_strategy(mock_callback, mock_state)

        update_kwargs = mock_state.update_data.await_args.kwargs
        assert update_kwargs["sales_strategy"] == "quick_call"
        assert [stage["stage"] for stage in update_kwargs["sales_funnel"]] == [
            "trust",
            "interest",
            "cta",
        ]
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.call_to_action)

    async def test_max_messages_invalid(self, mock_message, mock_state):
        mock_message.text = "abc"
        await process_script_max_messages(mock_message, mock_state)
        mock_state.update_data.assert_not_awaited()
        mock_message.answer.assert_called_once_with("❌ Введите число.")

    async def test_max_messages_valid(self, mock_message, mock_state):
        mock_message.text = "3"
        await process_script_max_messages(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(max_messages=3)
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.follow_up_delay_hours)

    async def test_delay_invalid(self, mock_message, mock_state):
        mock_message.text = "abc"
        await process_script_delay(mock_message, mock_state)
        mock_state.update_data.assert_not_awaited()
        mock_message.answer.assert_called_once_with("❌ Введите число.")

    async def test_delay_valid(self, mock_message, mock_state):
        mock_message.text = "48"
        await process_script_delay(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(follow_up_delay_hours=48)

    async def test_work_hours_default(self, mock_callback, mock_state):
        await process_work_hours_default(mock_callback, mock_state)
        mock_state.update_data.assert_any_await(working_hours_start=dt_time(9, 0))
        mock_state.update_data.assert_any_await(working_hours_end=dt_time(18, 0))
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.timezone)

    async def test_work_hours_manual(self, mock_callback, mock_state):
        await process_work_hours_manual(mock_callback, mock_state)
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.working_hours)

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
        mock_message.answer.assert_called_once()
        assert "Проверьте бизнес" in mock_message.answer.call_args[0][0]


class TestConfirmCreateScript:
    async def test_creates_script(self, mock_callback, mock_state):
        mock_state.get_data.return_value = {
            "name": "Test Script",
            "role_prompt": "Role",
            "target_audience": None,
            "goal": "Goal",
            "success_criteria": None,
            "tone": "professional",
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
        mock_callback.answer.assert_awaited_once_with("✅ Бизнес сохранен!")


class TestCancelCreateScript:
    async def test_clears_state(self, mock_callback, mock_state):
        await cancel_create_script(mock_callback, mock_state)
        mock_state.clear.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("❌ Создание отменено")


class TestCmdUpload:
    async def test_requests_file(self, mock_message, mock_state):
        await cmd_upload(mock_message, mock_state)
        mock_state.set_state.assert_awaited_with(CSVImportFSM.waiting_file)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "CSV" in text
        assert "Excel" in text
        assert "telegram_user_id" in text
        assert "telegram_id" in text
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


class TestCmdStartCampaign:
    async def test_no_draft_campaigns(self, mock_message, mock_state):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_startcampaign(mock_message, mock_state)

        mock_message.answer.assert_called_once()
        assert "Черновиков запуска нет" in mock_message.answer.call_args[0][0]

    async def test_shows_draft_campaigns(self, mock_message, mock_state):
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Draft Campaign",
            status="draft",
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [campaign]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_startcampaign(mock_message, mock_state)

        mock_state.set_state.assert_awaited_with(CampaignStartFSM.selecting)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Выберите сохраненный черновик" in text


class TestHandleStartcamp:
    async def test_cancels(self, mock_callback, mock_state):
        mock_callback.data = "startcamp:cancel"
        await handle_startcamp(mock_callback, mock_state)
        mock_state.clear.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("Отменено")

    async def test_invalid_uuid(self, mock_callback, mock_state):
        mock_callback.data = "startcamp:invalid"
        await handle_startcamp(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

    async def test_campaign_not_found(self, mock_callback, mock_state):
        mock_callback.data = f"startcamp:{uuid.uuid4()}"
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_startcamp(mock_callback, mock_state)

        mock_callback.answer.assert_awaited_once_with("❌ Запуск не найден")
        mock_state.clear.assert_awaited_once()


class TestCampaignCreateFSM:
    async def test_select_script_generates_preview(self, mock_callback, mock_state):
        script_id = uuid.uuid4()
        mock_callback.data = f"campaign_script:{script_id}"
        mock_state.get_data.return_value = {
            "records": [{"first_name": "Alice", "telegram_user_id": "123"}],
        }
        script = Script(
            id=script_id,
            name="Test Script",
            goal="Book",
            max_messages=2,
            tone="professional",
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = script
        context = _make_mock_session(result_mock)

        mock_engine = MagicMock()
        mock_engine.generate_response_with_guardrails = AsyncMock(
            return_value={"text": "Привет, Alice!"}
        )

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot.LLMEngine", return_value=mock_engine),
        ):
            await process_campaign_script(mock_callback, mock_state)

        mock_state.update_data.assert_any_await(script_id=script_id)
        mock_state.set_state.assert_awaited_with(CampaignCreateFSM.preview)
        text = mock_callback.message.edit_text.call_args[0][0]
        assert "Привет, Alice!" in text
        assert (
            "Запустить"
            in mock_callback.message.edit_text.call_args[1]["reply_markup"]
            .inline_keyboard[0][0]
            .text
        )
        mock_callback.message.answer.assert_not_awaited()

    async def test_preview_regenerate(self, mock_callback, mock_state):
        script_id = uuid.uuid4()
        mock_callback.data = "preview:regenerate"
        mock_callback.message.edit_text = AsyncMock()
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "records": [{"first_name": "Bob", "telegram_user_id": "456"}],
        }
        script = Script(
            id=script_id,
            name="Test Script",
            goal="Book",
            max_messages=2,
            tone="professional",
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = script
        context = _make_mock_session(result_mock)

        mock_engine = MagicMock()
        mock_engine.generate_response_with_guardrails = AsyncMock(
            return_value={"text": "Новое сообщение"}
        )

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot.LLMEngine", return_value=mock_engine),
        ):
            await handle_preview_regenerate(mock_callback, mock_state)

        mock_callback.message.edit_text.assert_called_once()
        assert "Новое сообщение" in mock_callback.message.edit_text.call_args[0][0]
        mock_callback.answer.assert_awaited_once_with("🔄 Обновлено")

    async def test_preview_regenerate_ignores_not_modified(
        self, mock_callback, mock_state
    ):
        script_id = uuid.uuid4()
        mock_callback.data = "preview:regenerate"
        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(),
                message=(
                    "Bad Request: message is not modified: specified new message "
                    "content and reply markup are exactly the same"
                ),
            )
        )
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "records": [{"first_name": "Bob", "telegram_user_id": "456"}],
        }
        script = Script(
            id=script_id,
            name="Test Script",
            goal="Book",
            max_messages=2,
            tone="professional",
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = script
        context = _make_mock_session(result_mock)

        mock_engine = MagicMock()
        mock_engine.generate_response_with_guardrails = AsyncMock(
            return_value={"text": "Новое сообщение"}
        )

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot.LLMEngine", return_value=mock_engine),
        ):
            await handle_preview_regenerate(mock_callback, mock_state)

        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("Без изменений")

    async def test_preview_uses_safe_fallback_when_guardrails_fallback(self):
        script = Script(
            id=uuid.uuid4(),
            name="Test Script",
            goal="Book",
            max_messages=2,
            tone="professional",
        )
        mock_engine = MagicMock()
        mock_engine.generate_response_with_guardrails = AsyncMock(
            return_value={
                "text": "Здравствуйте! Есть 15 минут на короткий созвон?",
                "model": "fallback",
                "tokens_used": 0,
            }
        )

        with patch("app.bots.admin_bot.LLMEngine", return_value=mock_engine):
            text = await _generate_preview_message(
                script,
                {"first_name": "Максим", "telegram_user_id": "123"},
            )

        assert "Привет, Максим" in text
        assert "Пишу коротко" in text
        assert "15 минут" not in text

    async def test_preview_launch_asks_name(self, mock_callback, mock_state):
        mock_callback.data = "preview:launch"
        await handle_preview_launch(mock_callback, mock_state)
        mock_state.set_state.assert_awaited_with(CampaignCreateFSM.name)
        mock_callback.message.answer.assert_called_once()
        assert (
            "назвать этот запуск" in mock_callback.message.answer.call_args[0][0].lower()
        )

    async def test_preview_change_script(self, mock_callback, mock_state):
        script_id = uuid.uuid4()
        mock_callback.data = "preview:change_script"
        mock_state.get_data.return_value = {
            "records": [{"first_name": "Alice", "telegram_user_id": "123"}],
        }
        script = Script(
            id=script_id,
            name="Test Script",
            goal="Book",
            max_messages=2,
            tone="professional",
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [script]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_preview_change_script(mock_callback, mock_state)

        mock_state.set_state.assert_awaited_with(CampaignCreateFSM.select_script)
        mock_callback.message.edit_text.assert_awaited_once()
        mock_callback.message.answer.assert_not_awaited()
        assert "Выберите бизнес" in mock_callback.message.edit_text.call_args[0][0]

    async def test_campaign_script_selection_cancel(self, mock_callback, mock_state):
        mock_callback.data = "campaign_select:cancel"

        await cancel_campaign_script_selection(mock_callback, mock_state)

        mock_state.clear.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("❌ Отменено")
        mock_callback.message.edit_text.assert_awaited_once_with(
            "Создание запуска отменено.",
            reply_markup=None,
            parse_mode=None,
        )


class TestBuildCampaignButtons:
    def test_draft_buttons(self):
        campaign = Campaign(id=uuid.uuid4(), name="Draft Campaign", status="draft")
        buttons = _build_campaign_buttons(campaign)
        assert len(buttons) == 2
        assert "▶️" in buttons[0].text
        assert buttons[0].callback_data.startswith("camp_start:")
        assert "🗑" in buttons[1].text
        assert buttons[1].callback_data.startswith("camp_delete:")

    def test_running_buttons(self):
        campaign = Campaign(id=uuid.uuid4(), name="Running Campaign", status="running")
        buttons = _build_campaign_buttons(campaign)
        assert len(buttons) == 2
        assert "⏸" in buttons[0].text
        assert buttons[0].callback_data.startswith("camp_pause:")
        assert "🗑" in buttons[1].text
        assert buttons[1].callback_data.startswith("camp_delete:")

    def test_paused_buttons(self):
        campaign = Campaign(id=uuid.uuid4(), name="Paused Campaign", status="paused")
        buttons = _build_campaign_buttons(campaign)
        assert len(buttons) == 2
        assert "▶️" in buttons[0].text
        assert buttons[0].callback_data.startswith("camp_resume:")
        assert "🗑" in buttons[1].text
        assert buttons[1].callback_data.startswith("camp_delete:")

    def test_closed_buttons(self):
        campaign = Campaign(id=uuid.uuid4(), name="Closed Campaign", status="closed")
        buttons = _build_campaign_buttons(campaign)
        assert len(buttons) == 1
        assert "🗑" in buttons[0].text
        assert buttons[0].callback_data.startswith("camp_delete:")


class TestSendOrEditCampaigns:
    @pytest.mark.asyncio
    async def test_sends_new_message_for_user_command(self, mock_message):
        from unittest.mock import AsyncMock, MagicMock
        from app.models.script import Script

        campaign = Campaign(
            id=uuid.uuid4(),
            name="Test Campaign",
            status="draft",
            script_id=uuid.uuid4(),
        )
        script = Script(id=campaign.script_id, name="Test Script")

        with patch(
            "app.bots.admin_bot._load_campaigns",
            new=AsyncMock(return_value=[(campaign, script)]),
        ):
            mock_message.from_user = MagicMock()
            mock_message.from_user.is_bot = False
            await _send_or_edit_campaigns(mock_message)

        mock_message.answer.assert_awaited_once()
        mock_message.edit_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_edits_message_for_bot_message(self, mock_message):
        from unittest.mock import AsyncMock, MagicMock
        from app.models.script import Script

        campaign = Campaign(
            id=uuid.uuid4(),
            name="Test Campaign",
            status="draft",
            script_id=uuid.uuid4(),
        )
        script = Script(id=campaign.script_id, name="Test Script")

        with patch(
            "app.bots.admin_bot._load_campaigns",
            new=AsyncMock(return_value=[(campaign, script)]),
        ):
            mock_message.from_user = MagicMock()
            mock_message.from_user.is_bot = True
            await _send_or_edit_campaigns(mock_message)

        mock_message.edit_text.assert_awaited_once()
        mock_message.answer.assert_not_called()


class TestCampActions:
    @pytest.mark.asyncio
    async def test_handle_camp_start_only_from_draft(self, mock_callback):
        from unittest.mock import MagicMock

        campaign = Campaign(id=uuid.uuid4(), name="Test", status="draft")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = campaign
        context = _make_mock_session(result_mock)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
            patch("app.bots.admin_bot._schedule_process_campaign"),
        ):
            mock_callback.data = f"camp_start:{campaign.id}"
            await handle_camp_start(mock_callback)

        assert campaign.status == "running"
        mock_callback.answer.assert_awaited_with("▶️ Запущено")

    @pytest.mark.asyncio
    async def test_handle_camp_start_ignores_fast_second_click(self, mock_callback):
        from unittest.mock import MagicMock

        campaign = Campaign(id=uuid.uuid4(), name="Test", status="draft")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = campaign
        context = _make_mock_session(result_mock)
        schedule = MagicMock()

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
            patch("app.bots.admin_bot._schedule_process_campaign", schedule),
        ):
            mock_callback.data = f"camp_start:{campaign.id}"
            await handle_camp_start(mock_callback)
            await handle_camp_start(mock_callback)

        assert campaign.status == "running"
        assert schedule.call_count == 1
        mock_callback.answer.assert_any_await("▶️ Запущено")
        mock_callback.answer.assert_any_await("❌ Запуск уже начат или не найден")

    @pytest.mark.asyncio
    async def test_handle_camp_start_rejects_malformed_callback_data(
        self, mock_callback
    ):
        mock_callback.data = "camp_start:not-a-uuid"

        with patch("app.bots.admin_bot.AsyncSessionLocal") as mock_session:
            await handle_camp_start(mock_callback)

        mock_session.assert_not_called()
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

    @pytest.mark.asyncio
    async def test_handle_camp_pause_only_from_running(self, mock_callback):
        from unittest.mock import MagicMock

        campaign = Campaign(id=uuid.uuid4(), name="Test", status="running")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = campaign
        context = _make_mock_session(result_mock)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_pause:{campaign.id}"
            await handle_camp_pause(mock_callback)

        assert campaign.status == "paused"
        mock_callback.answer.assert_awaited_with("⏸ Пауза")

    @pytest.mark.asyncio
    async def test_handle_camp_resume_only_from_paused(self, mock_callback):
        from unittest.mock import MagicMock

        campaign = Campaign(id=uuid.uuid4(), name="Test", status="paused")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = campaign
        context = _make_mock_session(result_mock)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_resume:{campaign.id}"
            await handle_camp_resume(mock_callback)

        assert campaign.status == "running"
        mock_callback.answer.assert_awaited_with("▶️ Возобновлено")

    @pytest.mark.asyncio
    async def test_handle_camp_delete_removes_dependent_records(self, mock_callback):
        from unittest.mock import MagicMock

        campaign = Campaign(id=uuid.uuid4(), name="Test", status="closed")
        conversation = Conversation(id=uuid.uuid4(), campaign_id=campaign.id)
        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign
        conv_ids_result = MagicMock()
        conv_ids_result.all.return_value = [(conversation.id,)]

        session = AsyncMock()
        session.execute.side_effect = [
            campaign_result,
            conv_ids_result,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        session.add = MagicMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_delete:{campaign.id}"
            await handle_camp_delete(mock_callback)

        assert session.execute.call_count == 5
        mock_callback.answer.assert_awaited_with("🗑 Удалено")
