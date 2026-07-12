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

from app.bots import admin_bot as admin_bot_module
from app.bots.admin_bot import (
    _format_scripts,
    _format_campaigns,
    _format_hotleads,
    _format_hotlead_detail,
    _hotlead_detail_keyboard,
    _format_analytics,
    _build_campaign_buttons,
    _build_script_buttons,
    _hotlead_overview_keyboard,
    _dispatch_navigation_override,
    _main_menu_keyboard,
    _notify_admin_error,
    _send_or_edit_scripts,
    _send_or_edit_campaigns,
    _parse_working_hours,
    _time_in_working_window,
    _launch_timing_notice,
    _launch_queue_notice,
    _conversation_id_from_row,
    _state_to_name_map,
    _existing_strategy_keyboard,
    _script_confirm_keyboard,
    _script_detail_keyboard,
    _script_edit_keyboard,
    _history_collapse_keyboard,
    _history_open_keyboard,
    _split_long_text,
    _telegram_search_missing_text,
    _discovery_config_error_text,
    handle_script_view,
    handle_script_edit_field,
    process_script_edit_value,
    handle_script_strategy_update,
    _generate_preview_message,
    _format_preview_text,
    _preview_keyboard,
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
    handle_history_collapse,
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
    handle_preview_show_all,
    handle_preview_show_first,
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
    callback.message.delete = AsyncMock()
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


def _inline_callback_data(keyboard_or_buttons):
    if isinstance(keyboard_or_buttons, list):
        buttons = keyboard_or_buttons
    else:
        buttons = [
            button
            for row in keyboard_or_buttons.inline_keyboard
            for button in row
        ]
    return [button.callback_data for button in buttons if button.callback_data]


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


class TestAdminPureHelpers:
    def test_user_id_resolution_covers_chat_and_nested_message_shapes(self):
        assert (
            admin_bot_module._user_id_from_event(
                SimpleNamespace(chat=SimpleNamespace(id=15))
            )
            == 15
        )
        assert (
            admin_bot_module._user_id_from_event(
                SimpleNamespace(
                    from_user=SimpleNamespace(id=10, is_bot=True),
                    chat=SimpleNamespace(id=20),
                )
            )
            == 20
        )
        assert (
            admin_bot_module._user_id_from_event(
                SimpleNamespace(
                    message=SimpleNamespace(
                        from_user=SimpleNamespace(id=30, is_bot=True),
                        chat=SimpleNamespace(id=40),
                    )
                )
            )
            == 40
        )
        assert (
            admin_bot_module._user_id_from_event(
                SimpleNamespace(
                    message=SimpleNamespace(
                        from_user=SimpleNamespace(id=45, is_bot=False)
                    )
                )
            )
            == 45
        )
        assert (
            admin_bot_module._user_id_from_event(
                SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=50)))
            )
            == 50
        )
        assert admin_bot_module._user_id_from_event(SimpleNamespace()) is None

    def test_welcome_text_and_prompt_localization_branches(self):
        assert "Готов к работе" in admin_bot_module._welcome_text(admin_bot_module.LANG_RU)
        assert "Ready." in admin_bot_module._welcome_text(LANG_EN)
        assert "Enter a short business" in admin_bot_module._script_field_prompt(
            "name", LANG_EN
        )
        assert "Enter the new value" in admin_bot_module._script_field_prompt(
            "unknown", LANG_EN
        )

    def test_parse_working_hours_accepts_strict_hh_mm_range(self):
        assert _parse_working_hours("09:30-18:45") == (
            dt_time(9, 30),
            dt_time(18, 45),
        )
        assert _parse_working_hours("09:00/18:00") is None
        assert _parse_working_hours("25:00-18:00") is None

    def test_time_in_working_window_supports_regular_and_overnight_ranges(self):
        assert _time_in_working_window(dt_time(10, 0), dt_time(9, 0), dt_time(18, 0))
        assert not _time_in_working_window(
            dt_time(18, 0), dt_time(9, 0), dt_time(18, 0)
        )
        assert _time_in_working_window(dt_time(23, 0), dt_time(22, 0), dt_time(6, 0))
        assert _time_in_working_window(dt_time(5, 30), dt_time(22, 0), dt_time(6, 0))
        assert not _time_in_working_window(
            dt_time(12, 0), dt_time(22, 0), dt_time(6, 0)
        )

    def test_launch_timing_notice_is_empty_inside_window(self, monkeypatch):
        from app.bots import admin_bot

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 7, 10, 12, 0, tzinfo=tz)

        monkeypatch.setattr(admin_bot, "datetime", FixedDatetime)
        script = Script(
            timezone="Europe/Moscow",
            working_hours_start=dt_time(9, 0),
            working_hours_end=dt_time(18, 0),
        )

        assert _launch_timing_notice(script) == ""

    def test_launch_timing_notice_warns_outside_window_and_falls_back_timezone(
        self, monkeypatch
    ):
        from app.bots import admin_bot

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 7, 10, 22, 0, tzinfo=tz)

        monkeypatch.setattr(admin_bot, "datetime", FixedDatetime)
        script = Script(
            timezone="Bad/Timezone",
            working_hours_start=dt_time(9, 0),
            working_hours_end=dt_time(18, 0),
        )

        text = _launch_timing_notice(script, LANG_EN)

        assert "outside this business's working hours" in text
        assert "09:00-18:00 Europe/Moscow" in text

    def test_launch_timing_notice_none_and_russian_outside_window(self, monkeypatch):
        from app.bots import admin_bot

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 7, 10, 22, 0, tzinfo=tz)

        monkeypatch.setattr(admin_bot, "datetime", FixedDatetime)
        assert _launch_timing_notice(None) == ""
        script = Script(
            timezone="Europe/Moscow",
            working_hours_start=dt_time(9, 0),
            working_hours_end=dt_time(18, 0),
        )

        text = _launch_timing_notice(script)

        assert "вне рабочих часов" in text
        assert "09:00-18:00 Europe/Moscow" in text

    def test_launch_queue_notice_explains_order_and_rate_limits(self):
        ru_text = _launch_queue_notice(3)
        en_text = _launch_queue_notice(21, LANG_EN)
        one_text = _launch_queue_notice(1)
        five_text = _launch_queue_notice(5)

        assert "порядок такой же, как в файле" in ru_text
        assert "каждые 5 минут" in ru_text
        assert "1 сообщения в 30 секунд" in ru_text
        assert "1 контакт" in one_text
        assert "5 контактов" in five_text
        assert "upload order" in en_text
        assert "every 5 minutes" in en_text
        assert "1 message per 30 seconds" in en_text

    def test_conversation_id_from_row_accepts_uuid_or_id_attribute_only(self):
        conv_id = uuid.uuid4()
        assert _conversation_id_from_row(None) is None
        assert _conversation_id_from_row(conv_id) == conv_id
        assert _conversation_id_from_row(SimpleNamespace(id=conv_id)) == conv_id
        assert _conversation_id_from_row(SimpleNamespace(id="not-a-uuid")) is None

    def test_format_hotlead_detail_escapes_contact_name_and_localizes_copy(self):
        conv = Conversation(
            id=uuid.uuid4(),
            current_state="hot",
            sentiment="positive",
            operator_status="ready_for_human",
        )
        contact = Contact(
            id=uuid.uuid4(),
            telegram_username="<lead&user>",
        )

        ru_text = _format_hotlead_detail(conv, contact)
        en_text = _format_hotlead_detail(conv, contact, LANG_EN)

        assert "&lt;lead&amp;user&gt;" in ru_text
        assert "Готов к работе" in ru_text
        assert "Status: ready for handoff" in en_text
        assert "Operator note: ready for human" in en_text

    def test_hotlead_detail_keyboard_keeps_action_callback_contracts(self):
        conv_id = uuid.uuid4()
        keyboard = _hotlead_detail_keyboard(conv_id, LANG_EN)

        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        ]

        assert callback_data == [
            f"history:{conv_id}:hotleads",
            f"qualify:{conv_id}",
            f"reject:{conv_id}",
            "hotleads:list",
        ]

    def test_state_to_name_map_contains_every_create_state(self):
        state_map = _state_to_name_map()
        assert state_map[ScriptCreateFSM.name.state] is ScriptCreateFSM.name
        assert state_map[ScriptCreateFSM.confirm.state] is ScriptCreateFSM.confirm
        assert len(state_map) == len(set(state_map))

    def test_existing_strategy_keyboard_contains_all_strategies_and_back_link(self):
        script_id = uuid.uuid4()
        keyboard = _existing_strategy_keyboard(script_id, LANG_EN)
        callback_data = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        ]

        assert callback_data[:4] == [
            f"ss:n:{script_id}",
            f"ss:q:{script_id}",
            f"ss:c:{script_id}",
            f"ss:l:{script_id}",
        ]
        assert callback_data[-1] == f"scriptv:{script_id}"
        assert all(len(data.encode("utf-8")) <= 64 for data in callback_data)

    def test_script_edit_keyboard_exposes_all_edit_fields(self):
        script = Script(id=uuid.uuid4(), name="Business", is_active=True)
        keyboard = _script_edit_keyboard(script)
        callback_data = {
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
        }

        assert {
            f"scriptf:name:{script.id}",
            f"scriptf:role:{script.id}",
            f"scriptf:aud:{script.id}",
            f"scriptf:goal:{script.id}",
            f"scriptf:crit:{script.id}",
            f"scriptf:tone:{script.id}",
            f"scriptf:strategy:{script.id}",
            f"scriptf:cta:{script.id}",
            f"scriptf:msg:{script.id}",
            f"scriptf:follow:{script.id}",
            f"scriptf:hours:{script.id}",
            f"scriptf:tz:{script.id}",
            f"scriptv:{script.id}",
        } == callback_data

    def test_admin_inline_keyboards_keep_callback_data_under_telegram_limit(self):
        script = Script(
            id=uuid.uuid4(),
            name="Business",
            goal="Book a call",
            is_active=True,
        )
        conv = Conversation(id=uuid.uuid4(), current_state="meeting_booked")
        contact = Contact(id=uuid.uuid4(), telegram_username="leaduser")
        callbacks = []

        keyboards = [
            _build_script_buttons([(script, 12)], LANG_EN),
            _script_detail_keyboard(script, campaign_count=12, lang=LANG_EN),
            _script_edit_keyboard(script, LANG_EN),
            _script_confirm_keyboard(LANG_EN),
            _existing_strategy_keyboard(script.id, LANG_EN),
            _hotlead_overview_keyboard([(conv, contact)], LANG_EN),
            _hotlead_detail_keyboard(conv.id, LANG_EN),
            _history_collapse_keyboard(conv.id, LANG_EN, origin="conversations"),
            _history_open_keyboard(conv.id, LANG_EN),
            _preview_keyboard(LANG_EN, records_count=50),
            _preview_keyboard(LANG_EN, records_count=50, showing_all=True),
        ]
        for keyboard in keyboards:
            callbacks.extend(_inline_callback_data(keyboard))

        for status in ("draft", "running", "paused", "completed"):
            campaign = Campaign(id=uuid.uuid4(), name=status, status=status)
            callbacks.extend(_inline_callback_data(_build_campaign_buttons(campaign, LANG_EN)))

        assert callbacks
        assert [
            data for data in callbacks if len(data.encode("utf-8")) > 64
        ] == []

    def test_script_detail_and_summary_english_and_empty_lists(self):
        script = Script(
            id=uuid.uuid4(),
            name="Cups",
            role_prompt="Custom cups",
            target_audience="Coffee shops",
            goal="Book calls",
            success_criteria="Meeting booked",
            tone="friendly",
            is_active=True,
            working_hours_start=dt_time(9, 0),
            working_hours_end=dt_time(18, 0),
            timezone="UTC",
        )

        assert "What we sell" in admin_bot_module._format_script_details(
            script, campaign_count=1, lang=LANG_EN
        )
        summary = admin_bot_module._script_create_summary(
            {
                "name": "Cups",
                "role_prompt": "Custom cups",
                "target_audience": "Coffee shops",
                "goal": "Book calls",
                "success_criteria": "Meeting booked",
                "tone": "friendly",
                "sales_strategy": "quick_call",
                "call_to_action": "quick call",
                "max_messages": 2,
                "follow_up_delay_hours": 12,
                "working_hours_start": dt_time(10, 0),
                "working_hours_end": dt_time(19, 0),
                "timezone": "UTC",
            },
            LANG_EN,
        )
        assert "Review the business" in summary
        assert "Sales funnel" in summary
        assert admin_bot_module._format_scripts([], LANG_EN) == ""
        assert admin_bot_module._state_label(None, LANG_EN) == "first touch"
        keyboard = _build_script_buttons([script], LANG_EN)
        callbacks = _inline_callback_data(keyboard)
        assert f"scriptv:{script.id}" in callbacks

    def test_contact_display_name_includes_phone_with_full_name(self):
        contact = Contact(
            id=uuid.uuid4(),
            first_name="Max",
            last_name="Lead",
            phone="+79990000000",
        )

        assert admin_bot_module._contact_display_name(contact) == "Max Lead · +79990000000"

    def test_hotlead_format_operator_status_and_russian_keyboard(self):
        conv = Conversation(
            id=uuid.uuid4(),
            current_state="hot",
            sentiment="positive",
            operator_status="ready_for_human",
        )
        contact = Contact(id=uuid.uuid4(), telegram_username="lead")

        ru_text = _format_hotleads([(conv, contact)])
        en_text = _format_hotleads([(conv, contact)], LANG_EN)
        keyboard = _hotlead_detail_keyboard(conv.id)

        assert "Ручная отметка" in ru_text
        assert "Operator note" in en_text
        assert f"history:{conv.id}:hotleads" in _inline_callback_data(keyboard)

    def test_split_long_text_prefers_paragraph_boundaries_and_truncates_huge_blocks(self):
        assert _split_long_text("short", max_len=10) == ["short"]

        chunks = _split_long_text("alpha\n\nbeta beta\n\ngamma", max_len=12)
        assert chunks == ["alpha", "beta beta", "gamma"]

        huge_chunks = _split_long_text("x" * 20, max_len=8)
        assert huge_chunks == ["x" * 8]
        assert _split_long_text("\n\n", max_len=8) == ["\n\n"]
        assert _split_long_text("alpha\n\n\n\nbeta", max_len=8) == ["alpha", "beta"]

    def test_discovery_missing_configuration_texts_are_source_specific(self):
        assert "No paid directory API token" in _telegram_search_missing_text(LANG_EN)
        assert "EXTERNAL_LEAD_API_URL" in _discovery_config_error_text(
            None, "external_api", LANG_EN
        )
        assert "TELEGRAM_API_ID" in _discovery_config_error_text(
            "telegram_api_missing", "telegram_search", LANG_EN
        )
        assert "session string" in _discovery_config_error_text(
            "telegram_account_missing", "telegram_search", LANG_EN
        )
        assert "could not start" in _discovery_config_error_text(
            "telegram_client_failed", "telegram_search", LANG_EN
        )


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

    async def test_language_choice_falls_back_when_edit_fails(self, mock_callback):
        user_id = 54321
        mock_callback.from_user = MagicMock(id=user_id)
        mock_callback.data = "lang:ru"
        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit message"
            )
        )

        await handle_language_choice(mock_callback)

        assert _admin_language_by_user[user_id] == "ru"
        assert mock_callback.message.answer.await_count == 2
        assert mock_callback.message.answer.await_args_list[0].args[0] == "Язык: русский"
        assert "Готов к работе" in mock_callback.message.answer.await_args_list[1].args[0]
        mock_callback.answer.assert_awaited_once_with("Язык сохранен")

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
    async def test_startup_shutdown_cancel_pending_command_registration(
        self, monkeypatch
    ):
        async def never_finishes(_bot):
            await asyncio.sleep(60)

        monkeypatch.setattr(admin_bot_module, "_set_admin_bot_commands", never_finishes)

        await admin_bot_module.on_startup(MagicMock())
        assert admin_bot_module._polling_active is True
        assert admin_bot_module._command_registration_task is not None

        await admin_bot_module.on_shutdown(MagicMock())

        assert admin_bot_module._polling_active is False
        assert admin_bot_module._command_registration_task is None

    async def test_set_admin_bot_commands_fails_after_retries(self, monkeypatch):
        bot = MagicMock()
        bot.set_my_commands = AsyncMock(side_effect=RuntimeError("telegram down"))
        monkeypatch.setattr(admin_bot_module, "COMMAND_REGISTRATION_ATTEMPTS", 2)
        monkeypatch.setattr(admin_bot_module, "COMMAND_REGISTRATION_RETRY_DELAY_S", 0)
        sleep_mock = AsyncMock()
        monkeypatch.setattr(admin_bot_module.asyncio, "sleep", sleep_mock)

        result = await _set_admin_bot_commands(bot)

        assert result is False
        assert bot.set_my_commands.await_count == 2
        sleep_mock.assert_awaited_once_with(0)

    async def test_set_admin_bot_commands_propagates_cancelled_error(self):
        bot = MagicMock()
        bot.set_my_commands = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await _set_admin_bot_commands(bot)

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

    async def test_shows_english_schema_when_language_is_english(self, mock_message):
        mock_message.from_user.id = 777
        _admin_language_by_user[777] = LANG_EN
        try:
            await cmd_help(mock_message)
        finally:
            _admin_language_by_user.pop(777, None)

        text = mock_message.answer.call_args[0][0]
        assert "Short map" in text
        assert "/upload — upload contacts and launch" in text
        assert "Запуск связывает" not in text


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


class TestScriptBackNavigation:
    async def test_send_script_state_prompt_covers_all_create_states(
        self, mock_message, mock_state
    ):
        for state_obj in admin_bot_module.SCRIPT_CREATE_STATE_ORDER:
            mock_message.answer.reset_mock()
            await admin_bot_module._send_script_state_prompt(
                mock_message, state_obj, mock_state
            )
            mock_state.set_state.assert_awaited_with(state_obj)
            mock_message.answer.assert_called()

        mock_message.answer.reset_mock()
        await admin_bot_module._send_script_state_prompt(
            mock_message, ScriptCreateFSM.confirm, mock_state
        )
        assert mock_state.set_state.await_args.args[0] is ScriptCreateFSM.confirm
        mock_message.answer.assert_called()

    async def test_maybe_return_to_confirm_sends_summary(self, mock_message, mock_state):
        mock_state.get_data.return_value = {
            "_return_to_confirm": True,
            "name": "Cups",
            "role_prompt": "Custom cups",
            "goal": "Book calls",
            "sales_strategy": "quick_call",
        }

        result = await admin_bot_module._maybe_return_to_script_confirm(
            mock_message, mock_state
        )

        assert result is True
        mock_state.update_data.assert_awaited_with(
            _return_to_confirm=False, _draft_edit_field=None
        )
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.confirm)
        assert "Проверьте бизнес" in mock_message.answer.call_args[0][0]

    async def test_maybe_return_to_confirm_returns_false_without_flag(
        self, mock_message, mock_state
    ):
        mock_state.get_data.return_value = {"_return_to_confirm": False}

        assert (
            await admin_bot_module._maybe_return_to_script_confirm(
                mock_message, mock_state
            )
            is False
        )

    async def test_go_back_rejects_unknown_state(self, mock_message, mock_state):
        mock_state.get_state.return_value = "Unknown:state"

        result = await admin_bot_module._go_script_create_back(mock_message, mock_state)

        assert result is False
        assert "нельзя сделать шаг назад" in mock_message.answer.call_args[0][0].lower()

    async def test_go_back_on_first_step_keeps_user_there(self, mock_message, mock_state):
        mock_state.get_state.return_value = ScriptCreateFSM.name.state

        result = await admin_bot_module._go_script_create_back(mock_message, mock_state)

        assert result is True
        assert "первый шаг" in mock_message.answer.call_args[0][0].lower()

    async def test_go_back_moves_to_previous_prompt(self, mock_message, mock_state):
        mock_state.get_state.return_value = ScriptCreateFSM.goal.state

        result = await admin_bot_module._go_script_create_back(mock_message, mock_state)

        assert result is True
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.target_audience)

    async def test_maybe_handle_back_text_and_command_back_fallback(
        self, mock_message, mock_state
    ):
        mock_message.text = "hello"
        assert (
            await admin_bot_module._maybe_handle_back_text(mock_message, mock_state)
            is False
        )

        mock_message.text = "back"
        mock_state.get_state.return_value = ScriptCreateFSM.goal.state
        assert (
            await admin_bot_module._maybe_handle_back_text(mock_message, mock_state)
            is True
        )

        mock_message.answer.reset_mock()
        mock_state.get_state.return_value = "bad"
        await admin_bot_module.cmd_back(mock_message, mock_state)
        assert "Активного мастера нет" in mock_message.answer.call_args[0][0]

    async def test_script_back_button_answers_callback(self, mock_callback, mock_state):
        mock_state.get_state.return_value = ScriptCreateFSM.goal.state

        await admin_bot_module.handle_script_back_button(mock_callback, mock_state)

        mock_callback.answer.assert_awaited_once()
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.target_audience)


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

    async def test_unknown_message_english_branches(self, mock_message, mock_state):
        mock_message.from_user.id = 903
        _admin_language_by_user[903] = LANG_EN
        mock_state.get_state.return_value = None

        await handle_unknown_message(mock_message, mock_state)

        assert "I did not understand" in mock_message.answer.call_args[0][0]

        mock_message.answer.reset_mock()
        mock_state.get_state.return_value = "ScriptCreateFSM:name"
        await handle_unknown_message(mock_message, mock_state)

        assert "setup wizard is active" in mock_message.answer.call_args[0][0]

    async def test_unknown_callback_is_answered(self, mock_callback):
        mock_callback.data = "stale:button"
        await handle_unknown_callback(mock_callback)
        mock_callback.answer.assert_awaited_once_with(
            "Не понял кнопку. Откройте /start или /help.", show_alert=True
        )
        mock_callback.message.answer.assert_awaited_once()

    async def test_unknown_callback_handles_answer_failure(self, mock_callback):
        mock_callback.data = "stale:button"
        mock_callback.message.answer = AsyncMock(side_effect=RuntimeError("blocked"))

        await handle_unknown_callback(mock_callback)

        mock_callback.answer.assert_awaited_once()

    async def test_global_error_notifies_message_user(self, mock_message):
        update = SimpleNamespace(message=mock_message, edited_message=None)
        notified = await _notify_admin_error(update)
        assert notified is True
        mock_message.answer.assert_called_once()
        assert "бот не упал молча" in mock_message.answer.call_args[0][0]

    async def test_global_error_notifies_callback_and_handles_failures(
        self, mock_callback, mock_message
    ):
        update = SimpleNamespace(callback_query=mock_callback, message=None)
        notified = await _notify_admin_error(update)
        assert notified is True
        mock_callback.answer.assert_awaited_once()
        mock_callback.message.answer.assert_awaited_once()

        mock_callback.answer = AsyncMock(side_effect=RuntimeError("answer down"))
        mock_callback.message.answer = AsyncMock(side_effect=RuntimeError("send down"))
        update = SimpleNamespace(callback_query=mock_callback, message=mock_message)
        notified = await _notify_admin_error(update)
        assert notified is True
        mock_message.answer.assert_called_once()

        mock_message.answer.reset_mock()
        mock_message.answer.side_effect = RuntimeError("send down")
        notified = await _notify_admin_error(
            SimpleNamespace(callback_query=None, message=mock_message)
        )
        assert notified is False

    async def test_admin_error_handler_returns_true(self):
        message = AsyncMock(spec=types.Message)
        message.answer = AsyncMock()
        event = SimpleNamespace(
            exception=RuntimeError("boom"),
            update=SimpleNamespace(message=message),
        )

        result = await admin_bot_module.handle_admin_error(event)

        assert result is True
        message.answer.assert_awaited_once()

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

    async def test_stateful_menu_inside_wizard_passes_state_and_plain_text_is_ignored(
        self, mock_message, mock_state
    ):
        handler = AsyncMock()
        original = MENU_HANDLERS[MENU_UPLOAD]
        MENU_HANDLERS[MENU_UPLOAD] = handler
        mock_message.text = MENU_UPLOAD
        try:
            handled = await _dispatch_navigation_override(mock_message, mock_state)
        finally:
            MENU_HANDLERS[MENU_UPLOAD] = original

        assert handled is True
        handler.assert_awaited_once_with(mock_message, mock_state)

        mock_message.text = "just text"
        handled = await _dispatch_navigation_override(mock_message, mock_state)
        assert handled is False

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

    async def test_navigation_override_non_text_and_stateful_command(
        self, mock_message, mock_state
    ):
        mock_message.text = ""
        assert await _dispatch_navigation_override(mock_message, mock_state) is False

        mock_message.text = "/upload@admin_bot"
        upload_mock = AsyncMock()
        original = admin_bot_module.COMMAND_HANDLERS["/upload"]
        admin_bot_module.COMMAND_HANDLERS["/upload"] = (upload_mock, True)
        try:
            handled = await _dispatch_navigation_override(mock_message, mock_state)
        finally:
            admin_bot_module.COMMAND_HANDLERS["/upload"] = original

        assert handled is True
        mock_state.clear.assert_awaited()
        upload_mock.assert_awaited_once_with(mock_message, mock_state)

    async def test_navigation_middleware_only_overrides_active_message_state(
        self, mock_message, mock_state
    ):
        middleware = admin_bot_module.NavigationOverrideMiddleware()
        handler = AsyncMock(return_value="handled")

        mock_state.get_state.return_value = "CSVImportFSM:waiting_file"
        with patch(
            "app.bots.admin_bot._dispatch_navigation_override",
            new=AsyncMock(return_value=True),
        ) as dispatch:
            result = await middleware(handler, mock_message, {"state": mock_state})
        assert result is None
        dispatch.assert_awaited_once_with(mock_message, mock_state)

        mock_state.get_state.return_value = None
        result = await middleware(handler, mock_message, {"state": mock_state})
        assert result == "handled"

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

    async def test_callback_guard_allows_matching_state(self, mock_callback, mock_state):
        middleware = CallbackStateGuardMiddleware()
        handler = AsyncMock(return_value="ok")
        mock_callback.data = "preview:launch"
        mock_state.get_state.return_value = CampaignCreateFSM.preview.state

        result = await middleware(handler, mock_callback, {"state": mock_state})

        assert result == "ok"
        handler.assert_awaited_once()

    async def test_callback_guard_blocks_without_message(self, mock_callback, mock_state):
        middleware = CallbackStateGuardMiddleware()
        handler = AsyncMock()
        mock_callback.data = "campaign:start_now"
        mock_callback.message = None
        mock_state.get_state.return_value = CampaignCreateFSM.preview.state

        result = await middleware(handler, mock_callback, {"state": mock_state})

        assert result is None
        mock_callback.answer.assert_awaited_once()
        handler.assert_not_awaited()


class TestCmdScripts:
    def test_bot_configuration_helpers(self, monkeypatch):
        monkeypatch.setattr(
            admin_bot_module,
            "is_configured_bot_token",
            lambda token: token == "ok",
        )
        monkeypatch.setattr(admin_bot_module.settings, "admin_bot_token", "ok")
        admin_bot_module._polling_active = True

        assert admin_bot_module.is_admin_bot_configured() is True
        assert admin_bot_module.is_admin_bot_running() is True

        admin_bot_module._polling_active = False

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

    async def test_empty_scripts_edits_bot_message(self, mock_message):
        mock_message.from_user.is_bot = True
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_scripts(mock_message)

        mock_message.edit_text.assert_awaited_once()
        mock_message.answer.assert_not_called()

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

    async def test_send_or_edit_scripts_ignores_not_modified_for_empty_bot_message(
        self, mock_message
    ):
        mock_message.from_user.is_bot = True
        mock_message.edit_text.side_effect = TelegramBadRequest(
            method=MagicMock(),
            message="Bad Request: message is not modified",
        )
        result_mock = MagicMock()
        result_mock.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await _send_or_edit_scripts(mock_message)

        mock_message.answer.assert_not_called()

    async def test_send_or_edit_scripts_compacts_too_long_bot_message(
        self, mock_message
    ):
        script = Script(id=uuid.uuid4(), name="Long", goal="G", is_active=True)
        mock_message.from_user.is_bot = True
        mock_message.edit_text = AsyncMock(
            side_effect=[
                TelegramBadRequest(
                    method=MagicMock(), message="Bad Request: message is too long"
                ),
                None,
            ]
        )
        result_mock = MagicMock()
        result_mock.all.return_value = [(script, 0)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await _send_or_edit_scripts(mock_message)

        assert mock_message.edit_text.await_count == 2
        assert "Список бизнесов большой" in mock_message.edit_text.await_args.args[0]

    async def test_send_or_edit_scripts_compacts_too_long_new_message(
        self, mock_message
    ):
        script = Script(id=uuid.uuid4(), name="Long", goal="G", is_active=True)
        mock_message.answer = AsyncMock(
            side_effect=[
                TelegramBadRequest(
                    method=MagicMock(), message="Bad Request: message is too long"
                ),
                None,
            ]
        )
        result_mock = MagicMock()
        result_mock.all.return_value = [(script, 0)]
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await _send_or_edit_scripts(mock_message)

        assert mock_message.answer.await_count == 2
        assert "Список бизнесов большой" in mock_message.answer.await_args.args[0]

    async def test_send_or_edit_scripts_reraises_real_telegram_errors(
        self, mock_message
    ):
        mock_message.from_user.is_bot = True
        mock_message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit"
            )
        )
        with (
            patch(
                "app.bots.admin_bot._load_scripts_with_campaign_counts",
                new=AsyncMock(return_value=[]),
            ),
            pytest.raises(TelegramBadRequest),
        ):
            await _send_or_edit_scripts(mock_message)

        script = Script(id=uuid.uuid4(), name="Long", goal="G", is_active=True)
        mock_message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit"
            )
        )
        with (
            patch(
                "app.bots.admin_bot._load_scripts_with_campaign_counts",
                new=AsyncMock(return_value=[(script, 0)]),
            ),
            pytest.raises(TelegramBadRequest),
        ):
            await _send_or_edit_scripts(mock_message)

        mock_message.from_user.is_bot = False
        mock_message.answer = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot send"
            )
        )
        with (
            patch(
                "app.bots.admin_bot._load_scripts_with_campaign_counts",
                new=AsyncMock(return_value=[(script, 0)]),
            ),
            pytest.raises(TelegramBadRequest),
        ):
            await _send_or_edit_scripts(mock_message)

    async def test_refresh_scripts_and_new_script_callback(
        self, mock_callback, mock_state
    ):
        with patch("app.bots.admin_bot.cmd_scripts", new=AsyncMock()) as scripts_mock:
            await admin_bot_module.refresh_scripts(mock_callback)
        scripts_mock.assert_awaited_once_with(mock_callback.message)
        mock_callback.answer.assert_awaited_once()

        mock_callback.answer.reset_mock()
        with patch("app.bots.admin_bot.cmd_newscript", new=AsyncMock()) as new_mock:
            await admin_bot_module.handle_script_new(mock_callback, mock_state)
        new_mock.assert_awaited_once_with(mock_callback.message, mock_state)
        mock_callback.answer.assert_awaited_once()

    async def test_load_script_with_campaign_count_not_found(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        context = _make_mock_session(result)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            script, count = await admin_bot_module._load_script_with_campaign_count(
                uuid.uuid4()
            )

        assert script is None
        assert count == 0

    async def test_handle_scripts_list_callback(self, mock_callback):
        with patch(
            "app.bots.admin_bot._send_or_edit_scripts", new=AsyncMock()
        ) as list_mock:
            await admin_bot_module.handle_scripts_list(mock_callback)

        list_mock.assert_awaited_once_with(mock_callback.message)
        mock_callback.answer.assert_awaited_once()

    async def test_script_view_invalid_and_not_found(self, mock_callback):
        mock_callback.data = "scriptv:not-a-uuid"
        await handle_script_view(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

        mock_callback.answer.reset_mock()
        mock_callback.data = f"scriptv:{uuid.uuid4()}"
        with patch(
            "app.bots.admin_bot._load_script_with_campaign_count",
            new=AsyncMock(return_value=(None, 0)),
        ):
            await handle_script_view(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")

    async def test_script_edit_opens_keyboard_and_handles_errors(self, mock_callback):
        mock_callback.data = "scripte:not-a-uuid"
        await admin_bot_module.handle_script_edit(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

        mock_callback.answer.reset_mock()
        mock_callback.data = f"scripte:{uuid.uuid4()}"
        with patch(
            "app.bots.admin_bot._load_script_with_campaign_count",
            new=AsyncMock(return_value=(None, 0)),
        ):
            await admin_bot_module.handle_script_edit(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")

        mock_callback.answer.reset_mock()
        script = Script(id=uuid.uuid4(), name="Biz", goal="Goal", is_active=True)
        mock_callback.data = f"scripte:{script.id}"
        with (
            patch(
                "app.bots.admin_bot._load_script_with_campaign_count",
                new=AsyncMock(return_value=(script, 0)),
            ),
            patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock,
        ):
            await admin_bot_module.handle_script_edit(mock_callback)
        send_mock.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()

    async def test_script_edit_field_invalid_not_found_and_strategy(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "scriptf:bad:not-a-uuid"
        await handle_script_edit_field(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Неверное поле")

        mock_callback.answer.reset_mock()
        mock_callback.data = f"scriptf:name:{uuid.uuid4()}"
        with patch(
            "app.bots.admin_bot._load_script_with_campaign_count",
            new=AsyncMock(return_value=(None, 0)),
        ):
            await handle_script_edit_field(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")

        mock_callback.answer.reset_mock()
        script = Script(id=uuid.uuid4(), name="Biz", goal="Goal")
        mock_callback.data = f"scriptf:strategy:{script.id}"
        with (
            patch(
                "app.bots.admin_bot._load_script_with_campaign_count",
                new=AsyncMock(return_value=(script, 0)),
            ),
            patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock,
        ):
            await handle_script_edit_field(mock_callback, mock_state)
        send_mock.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()

    async def test_script_edit_value_session_and_validation_errors(
        self, mock_message, mock_state
    ):
        mock_state.get_data.return_value = {}
        await process_script_edit_value(mock_message, mock_state)
        mock_state.clear.assert_awaited()
        assert "устарела" in mock_message.answer.call_args[0][0]

        mock_state.clear.reset_mock()
        mock_message.answer.reset_mock()
        mock_state.get_data.return_value = {
            "edit_script_id": "not-a-uuid",
            "edit_field": "name",
        }
        await process_script_edit_value(mock_message, mock_state)
        mock_state.clear.assert_awaited()
        assert "Неверный ID" in mock_message.answer.call_args[0][0]

        cases = [
            ("name", "", "не может быть пустым"),
            ("tone", "wild", "professional"),
            ("max_messages", "NaN", "Введите число"),
            ("follow_up_delay_hours", "0", "больше нуля"),
            ("timezone", "mop", "Не понял часовой пояс"),
            ("working_hours", "9 to 6", "формате HH:MM"),
        ]
        for field, text, expected in cases:
            mock_message.answer.reset_mock()
            mock_state.get_data.return_value = {
                "edit_script_id": str(uuid.uuid4()),
                "edit_field": field,
            }
            mock_message.text = text
            await process_script_edit_value(mock_message, mock_state)
            assert expected in mock_message.answer.call_args[0][0]

    async def test_script_edit_value_not_found_and_nullable_field(
        self, mock_message, mock_state
    ):
        script_id = uuid.uuid4()
        mock_state.get_data.return_value = {
            "edit_script_id": str(script_id),
            "edit_field": "target_audience",
        }
        mock_message.text = "-"
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        context = _make_mock_session(result)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await process_script_edit_value(mock_message, mock_state)

        mock_state.clear.assert_awaited()
        assert "Бизнес не найден" in mock_message.answer.call_args[0][0]


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

    async def test_script_strategy_update_uses_short_callback_and_saves(
        self, mock_callback
    ):
        script = Script(id=uuid.uuid4(), name="Biz", role_prompt="Role", goal="Goal")
        result = MagicMock()
        result.scalar_one_or_none.return_value = script
        context = _make_mock_session(result)

        mock_callback.data = f"ss:l:{script.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_script_strategy_update(mock_callback)

        assert len(mock_callback.data.encode("utf-8")) <= 64
        assert script.sales_funnel
        assert any(stage["stage"] == "authority_timing" for stage in script.sales_funnel)
        mock_callback.answer.assert_awaited_once_with("✅ Сохранено")
        mock_callback.message.edit_text.assert_awaited_once()

    async def test_script_strategy_update_keeps_legacy_callback_compatible(
        self, mock_callback
    ):
        script = Script(id=uuid.uuid4(), name="Biz", role_prompt="Role", goal="Goal")
        result = MagicMock()
        result.scalar_one_or_none.return_value = script
        context = _make_mock_session(result)

        mock_callback.data = f"script_strategy:quick_call:{script.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_script_strategy_update(mock_callback)

        assert script.sales_funnel[1]["stage"] == "interest"
        mock_callback.answer.assert_awaited_once_with("✅ Сохранено")

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

    async def test_script_edit_value_updates_working_hours(
        self, mock_message, mock_state
    ):
        script = Script(
            id=uuid.uuid4(),
            name="Biz",
            role_prompt="Role",
            goal="Goal",
            working_hours_start=dt_time(9, 0),
            working_hours_end=dt_time(18, 0),
        )
        mock_state.get_data.return_value = {
            "edit_script_id": str(script.id),
            "edit_field": "working_hours",
        }
        mock_message.text = "10:30-19:45"
        result = MagicMock()
        result.scalar_one_or_none.return_value = script
        context = _make_mock_session(result)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await process_script_edit_value(mock_message, mock_state)

        assert script.working_hours_start == dt_time(10, 30)
        assert script.working_hours_end == dt_time(19, 45)
        mock_state.clear.assert_awaited_once()
        assert "Сохранил" in mock_message.answer.call_args[0][0]

    async def test_script_strategy_update_invalid_and_not_found(self, mock_callback):
        mock_callback.data = "ss:bad:not-a-uuid"
        await handle_script_strategy_update(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

        mock_callback.answer.reset_mock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        context = _make_mock_session(result)
        mock_callback.data = f"ss:q:{uuid.uuid4()}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_script_strategy_update(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")

    async def test_script_toggle_invalid_and_not_found(self, mock_callback):
        mock_callback.data = "script_toggle:not-a-uuid"
        await handle_script_toggle(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

        mock_callback.answer.reset_mock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        context = _make_mock_session(result)
        mock_callback.data = f"script_toggle:{uuid.uuid4()}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_script_toggle(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")

    async def test_script_delete_not_found_after_usage_check(self, mock_callback):
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.side_effect = [count_result, script_result]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)
        mock_callback.data = f"script_delete:{uuid.uuid4()}:0"

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_script_delete(mock_callback)

        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")


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

    async def test_refresh_analytics_reuses_command(self, mock_callback):
        with patch("app.bots.admin_bot.cmd_analytics", new=AsyncMock()) as cmd_mock:
            await admin_bot_module.refresh_analytics(mock_callback)

        cmd_mock.assert_awaited_once_with(mock_callback.message)
        mock_callback.answer.assert_awaited_once()

    async def test_export_analytics_sends_csv_document(self, mock_callback):
        contact = Contact(
            id=uuid.uuid4(),
            telegram_username="lead",
            first_name="Lead",
            last_name="One",
            company_name="Acme",
            position="CEO",
        )
        campaign = Campaign(id=uuid.uuid4(), name="Launch", status="running")
        cc = admin_bot_module.CampaignContact(status="initial_sent")
        result = MagicMock()
        result.all.return_value = [(contact, campaign, cc)]
        context = _make_mock_session(result)
        bot = AsyncMock()
        mock_callback.message.chat = MagicMock(id=777)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._get_bot", return_value=bot),
        ):
            await admin_bot_module.export_analytics(mock_callback)

        bot.send_document.assert_awaited_once()
        kwargs = bot.send_document.await_args.kwargs
        assert kwargs["chat_id"] == 777
        assert kwargs["document"].filename == "analytics.csv"
        assert "Аналитика" in kwargs["caption"]
        mock_callback.answer.assert_awaited_once_with("📋 Файл отправлен")


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

    async def test_edit_hotleads_overview_empty_and_non_empty(self, mock_callback):
        with (
            patch("app.bots.admin_bot._load_hotleads", new=AsyncMock(return_value=[])),
            patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock,
        ):
            await admin_bot_module._edit_hotleads_overview(mock_callback)

        send_mock.assert_awaited_once()
        assert "Горячих лидов пока нет" in send_mock.await_args.args[1]

        send_mock.reset_mock()
        conv = Conversation(id=uuid.uuid4(), current_state="hot", sentiment="positive")
        contact = Contact(id=uuid.uuid4(), telegram_username="lead")
        with (
            patch(
                "app.bots.admin_bot._load_hotleads",
                new=AsyncMock(return_value=[(conv, contact)]),
            ),
            patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock,
        ):
            await admin_bot_module._edit_hotleads_overview(mock_callback)

        send_mock.assert_awaited_once()
        assert "Горячие лиды" in send_mock.await_args.args[1]
        assert send_mock.await_args.kwargs["parse_mode"] == "HTML"

    async def test_refresh_and_list_hotleads_callbacks(self, mock_callback):
        with patch(
            "app.bots.admin_bot._edit_hotleads_overview", new=AsyncMock()
        ) as edit_mock:
            await admin_bot_module.refresh_hotleads(mock_callback)
            await admin_bot_module.handle_hotleads_list(mock_callback)

        assert edit_mock.await_count == 2
        assert mock_callback.answer.await_count == 2

    async def test_hotlead_card_invalid_missing_and_success(self, mock_callback):
        mock_callback.data = "lead:not-a-uuid"
        await admin_bot_module.handle_hotlead_card(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID диалога")

        mock_callback.answer.reset_mock()
        result = MagicMock()
        result.first.return_value = None
        context = _make_mock_session(result)
        mock_callback.data = f"lead:{uuid.uuid4()}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await admin_bot_module.handle_hotlead_card(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Диалог не найден")

        mock_callback.answer.reset_mock()
        conv = Conversation(id=uuid.uuid4(), current_state="meeting_booked")
        contact = Contact(id=uuid.uuid4(), telegram_username="lead")
        result.first.return_value = (conv, contact)
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock,
        ):
            mock_callback.data = f"lead:{conv.id}"
            await admin_bot_module.handle_hotlead_card(mock_callback)
        send_mock.assert_awaited_once()
        assert "lead" in send_mock.await_args.args[1]
        mock_callback.answer.assert_awaited_once()


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

    async def test_find_conversation_by_uuid_and_text_query(self):
        conv_id = uuid.uuid4()
        uuid_result = MagicMock()
        uuid_result.scalar_one_or_none.return_value = SimpleNamespace(id=conv_id)
        context = _make_mock_session(uuid_result)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            found = await admin_bot_module._find_conversation_id_by_query(str(conv_id))
        assert found == conv_id

        text_result = MagicMock()
        text_result.scalar_one_or_none.return_value = conv_id
        context = _make_mock_session(text_result)
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            found = await admin_bot_module._find_conversation_id_by_query("@lead")
        assert found == conv_id

    async def test_find_conversation_uuid_falls_back_to_text_search(self):
        conv_id = uuid.uuid4()
        uuid_not_found = MagicMock()
        uuid_not_found.scalar_one_or_none.return_value = None
        text_result = MagicMock()
        text_result.scalar_one_or_none.return_value = conv_id
        session = AsyncMock()
        session.execute.side_effect = [uuid_not_found, text_result]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            found = await admin_bot_module._find_conversation_id_by_query(str(uuid.uuid4()))

        assert found == conv_id

    async def test_load_conversation_messages_reads_ordered_messages(self):
        conv_id = uuid.uuid4()
        msg = Message(id=uuid.uuid4(), conversation_id=conv_id, content="Hello")
        result = MagicMock()
        result.scalars.return_value.all.return_value = [msg]
        context = _make_mock_session(result)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            messages = await admin_bot_module._load_conversation_messages(conv_id)

        assert messages == [msg]


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

    async def test_qualifies_conversation_in_english(self, mock_callback):
        conv = Conversation(id=uuid.uuid4(), current_state="hot")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = conv
        context = _make_mock_session(result_mock)
        mock_callback.from_user = MagicMock(id=901, is_bot=False)
        _admin_language_by_user[901] = LANG_EN

        mock_callback.data = f"qualify:{conv.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_qualify(mock_callback)

        assert conv.operator_status == "qualified"
        mock_callback.answer.assert_awaited_once_with("✅ Marked as qualified")

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

    async def test_rejects_conversation_in_english(self, mock_callback):
        conv = Conversation(id=uuid.uuid4(), current_state="hot")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = conv
        context = _make_mock_session(result_mock)
        mock_callback.from_user = MagicMock(id=902, is_bot=False)
        _admin_language_by_user[902] = LANG_EN

        mock_callback.data = f"reject:{conv.id}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_reject(mock_callback)

        assert conv.operator_status == "rejected"
        mock_callback.answer.assert_awaited_once_with("🚫 Marked as not a fit")

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
        keyboard = mock_callback.message.answer.call_args.kwargs["reply_markup"]
        assert "🤖" in text
        assert "👤" in text
        assert "10:30 01.01" in text
        assert "Hello" in text
        callback_data = keyboard.inline_keyboard[0][0].callback_data
        assert callback_data == f"hc:{conv_id}:m"
        assert len(callback_data.encode("utf-8")) <= 64
        assert "Свернуть диалог" in keyboard.inline_keyboard[0][0].text
        mock_callback.answer.assert_awaited_once()

    async def test_history_from_conversations_uses_short_collapse_callback(
        self, mock_callback
    ):
        conv_id = uuid.uuid4()
        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            direction="outbound",
            content="Hello",
            sent_at=datetime(2024, 1, 1, 10, 30),
        )
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [msg]
        context = _make_mock_session(result_mock)

        mock_callback.data = f"history:{conv_id}:conversations"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_history(mock_callback)

        keyboard = mock_callback.message.answer.call_args.kwargs["reply_markup"]
        callback_data = keyboard.inline_keyboard[0][0].callback_data
        assert callback_data == f"hc:{conv_id}:c"
        assert len(callback_data.encode("utf-8")) <= 64

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

    async def test_parse_history_callback_rejects_wrong_prefix(self):
        with pytest.raises(ValueError):
            admin_bot_module._parse_history_callback_data("dialog:not-history", "history")

    async def test_collapse_deletes_history_without_new_text(self, mock_callback):
        conv_id = uuid.uuid4()
        mock_callback.data = f"hc:{conv_id}:h"

        await handle_history_collapse(mock_callback)

        mock_callback.message.delete.assert_awaited_once()
        mock_callback.message.edit_text.assert_not_awaited()
        mock_callback.message.answer.assert_not_awaited()
        mock_callback.answer.assert_awaited_once()

    async def test_collapse_invalid_and_delete_error_are_handled(self, mock_callback):
        mock_callback.data = "hc:not-a-uuid:h"
        await handle_history_collapse(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID диалога")

        mock_callback.answer.reset_mock()
        conv_id = uuid.uuid4()
        mock_callback.data = f"hc:{conv_id}:h"
        mock_callback.message.delete = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: message to delete not found"
            )
        )

        await handle_history_collapse(mock_callback)

        mock_callback.message.delete.assert_awaited_once()
        mock_callback.answer.assert_awaited_once()


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
    async def test_required_text_fields_reject_empty_values(self, mock_message, mock_state):
        cases = [
            (process_script_name, "Название не может быть пустым."),
            (process_script_role, "Описание бизнеса не может быть пустым."),
            (process_script_goal, "Цель не может быть пустой."),
            (admin_bot_module.process_script_call_to_action, "Следующий шаг не может быть пустым."),
        ]
        for handler, expected in cases:
            mock_message.answer.reset_mock()
            mock_state.update_data.reset_mock()
            mock_message.text = "   "

            await handler(mock_message, mock_state)

            mock_state.update_data.assert_not_awaited()
            mock_message.answer.assert_called_once_with(expected)

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

    async def test_first_message_goal_legacy_callback_moves_to_cta(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "fmg:trust"

        await admin_bot_module.process_script_first_message_goal(
            mock_callback, mock_state
        )

        mock_state.update_data.assert_awaited_once_with(first_message_goal="trust")
        mock_state.set_state.assert_awaited_once_with(ScriptCreateFSM.call_to_action)
        assert "call_to_action" in mock_callback.message.answer.call_args[0][0]
        mock_callback.answer.assert_awaited_once()

    async def test_call_to_action_valid(self, mock_message, mock_state):
        mock_message.text = "short call"

        await admin_bot_module.process_script_call_to_action(mock_message, mock_state)

        mock_state.update_data.assert_awaited_with(call_to_action="short call")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.follow_up_delay_hours)
        assert "напоминание" in mock_message.answer.call_args[0][0].lower()

    async def test_language_defaults_unknown_to_russian(self, mock_message, mock_state):
        mock_message.text = "de"

        await admin_bot_module.process_script_language(mock_message, mock_state)

        mock_state.update_data.assert_awaited_once_with(language="ru")
        mock_state.set_state.assert_awaited_once_with(ScriptCreateFSM.emoji_policy)
        keyboard = mock_message.answer.call_args.kwargs["reply_markup"]
        assert keyboard.inline_keyboard[0][0].text == "Запрещены"

    async def test_emoji_policy_to_max_first_message_length(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "emoji:rare"

        await admin_bot_module.process_script_emoji_policy(mock_callback, mock_state)

        mock_state.update_data.assert_awaited_once_with(emoji_policy="rare")
        mock_state.set_state.assert_awaited_once_with(
            ScriptCreateFSM.max_first_message_length
        )
        mock_callback.answer.assert_awaited_once()

    async def test_max_first_message_length_invalid_and_valid(
        self, mock_message, mock_state
    ):
        mock_message.text = "abc"
        await admin_bot_module.process_script_max_first_message_length(
            mock_message, mock_state
        )
        mock_message.answer.assert_called_once_with("❌ Введите число.")

        mock_message.answer.reset_mock()
        mock_state.update_data.reset_mock()
        mock_state.set_state.reset_mock()
        mock_message.text = "220"
        await admin_bot_module.process_script_max_first_message_length(
            mock_message, mock_state
        )

        mock_state.update_data.assert_awaited_once_with(max_first_message_length=220)
        mock_state.set_state.assert_awaited_once_with(ScriptCreateFSM.max_messages)
        assert "максимальное количество" in mock_message.answer.call_args[0][0]

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

    async def test_delay_rejects_zero(self, mock_message, mock_state):
        mock_message.text = "0"
        await process_script_delay(mock_message, mock_state)
        mock_state.update_data.assert_not_awaited()
        mock_message.answer.assert_called_once_with("Введите число больше нуля.")

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

    async def test_work_hours_single_message_range(self, mock_message, mock_state):
        mock_message.text = "08:30-17:45"

        await admin_bot_module.process_script_work_start(mock_message, mock_state)

        mock_state.update_data.assert_any_await(working_hours_start=dt_time(8, 30))
        mock_state.update_data.assert_any_await(working_hours_end=dt_time(17, 45))
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.timezone)

    async def test_work_hours_two_step_start_and_end(self, mock_message, mock_state):
        mock_message.text = "08:30"

        await admin_bot_module.process_script_work_start(mock_message, mock_state)

        mock_state.update_data.assert_awaited_with(_start_tmp="08:30")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.working_hours_end)

        mock_message.answer.reset_mock()
        mock_state.update_data.reset_mock()
        mock_state.set_state.reset_mock()
        mock_state.get_data.return_value = {"_start_tmp": "08:30"}
        mock_message.text = "17:45"

        await admin_bot_module.process_script_work_end(mock_message, mock_state)

        mock_state.update_data.assert_any_await(working_hours_start=dt_time(8, 30))
        mock_state.update_data.assert_any_await(working_hours_end=dt_time(17, 45))
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.timezone)

    async def test_work_hours_invalid_formats(self, mock_message, mock_state):
        mock_message.text = "bad"
        await admin_bot_module.process_script_work_start(mock_message, mock_state)
        assert "Неверный формат" in mock_message.answer.call_args[0][0]

        mock_message.answer.reset_mock()
        mock_state.get_data.return_value = {"_start_tmp": "08:30"}
        mock_message.text = "bad"
        await admin_bot_module.process_script_work_end(mock_message, mock_state)
        assert "Неверный формат" in mock_message.answer.call_args[0][0]

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

    async def test_timezone_rejects_unknown_value(self, mock_message, mock_state):
        mock_message.text = "mop"

        await process_script_timezone(mock_message, mock_state)

        assert "Не понял часовой пояс" in mock_message.answer.call_args[0][0]
        mock_state.update_data.assert_not_awaited()

    async def test_draft_edit_invalid_field_and_all_prompt_branches(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "sdedit:unknown"
        await admin_bot_module.handle_script_draft_edit(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Неверное поле")

        cases = [
            ("tone", ScriptCreateFSM.tone, "стиль общения"),
            ("strategy", ScriptCreateFSM.sales_strategy, "воронку продаж"),
            ("hours", ScriptCreateFSM.working_hours, "рабочие часы"),
            ("name", ScriptCreateFSM.name, "название"),
        ]
        for key, expected_state, expected_text in cases:
            mock_callback.answer.reset_mock()
            mock_state.update_data.reset_mock()
            mock_state.set_state.reset_mock()
            mock_callback.data = f"sdedit:{key}"
            with patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock:
                await admin_bot_module.handle_script_draft_edit(
                    mock_callback, mock_state
                )

            mock_state.update_data.assert_awaited()
            mock_state.set_state.assert_awaited_with(expected_state)
            assert expected_text in send_mock.await_args.args[1].lower()
            mock_callback.answer.assert_awaited_once()

    async def test_script_handlers_return_immediately_on_back_text(
        self, mock_message, mock_state
    ):
        handlers = [
            process_script_name,
            process_script_role,
            process_script_audience,
            process_script_goal,
            process_script_criteria,
            admin_bot_module.process_script_call_to_action,
            process_script_max_messages,
            process_script_delay,
            admin_bot_module.process_script_work_start,
            admin_bot_module.process_script_work_end,
            process_script_timezone,
        ]
        mock_message.text = "anything"
        for handler in handlers:
            mock_state.update_data.reset_mock()
            with patch(
                "app.bots.admin_bot._maybe_handle_back_text",
                new=AsyncMock(return_value=True),
            ):
                await handler(mock_message, mock_state)
            mock_state.update_data.assert_not_awaited()

    async def test_script_handlers_return_to_confirm_after_field_update(
        self, mock_message, mock_callback, mock_state
    ):
        message_handlers = [
            (process_script_name, "Name"),
            (process_script_role, "Role"),
            (process_script_audience, "Audience"),
            (process_script_goal, "Goal"),
            (process_script_criteria, "Criteria"),
            (admin_bot_module.process_script_call_to_action, "CTA"),
            (process_script_max_messages, "3"),
            (process_script_delay, "24"),
            (admin_bot_module.process_script_work_start, "09:00-18:00"),
        ]
        for handler, text in message_handlers:
            mock_message.text = text
            mock_state.set_state.reset_mock()
            with patch(
                "app.bots.admin_bot._maybe_return_to_script_confirm",
                new=AsyncMock(return_value=True),
            ):
                await handler(mock_message, mock_state)
            mock_state.set_state.assert_not_awaited()

        mock_callback.data = "tone:Деловой"
        with patch(
            "app.bots.admin_bot._maybe_return_to_script_confirm",
            new=AsyncMock(return_value=True),
        ):
            await process_script_tone(mock_callback, mock_state)
        mock_callback.answer.assert_awaited()

        mock_callback.answer.reset_mock()
        mock_callback.data = "strategy:quick_call"
        with patch(
            "app.bots.admin_bot._maybe_return_to_script_confirm",
            new=AsyncMock(return_value=True),
        ):
            await process_script_strategy(mock_callback, mock_state)
        mock_callback.answer.assert_awaited()

        mock_callback.answer.reset_mock()
        with patch(
            "app.bots.admin_bot._maybe_return_to_script_confirm",
            new=AsyncMock(return_value=True),
        ):
            await process_work_hours_default(mock_callback, mock_state)
        mock_callback.answer.assert_awaited()

        mock_message.text = "18:00"
        mock_state.get_data.return_value = {"_start_tmp": "09:00"}
        mock_state.set_state.reset_mock()
        with patch(
            "app.bots.admin_bot._maybe_return_to_script_confirm",
            new=AsyncMock(return_value=True),
        ):
            await admin_bot_module.process_script_work_end(mock_message, mock_state)
        mock_state.set_state.assert_not_awaited()


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

    async def test_requests_file_in_english(self, mock_message, mock_state):
        mock_message.from_user.id = 904
        _admin_language_by_user[904] = LANG_EN

        await cmd_upload(mock_message, mock_state)

        text = mock_message.answer.call_args[0][0]
        assert "Upload contacts" in text
        assert "John,Doe" in text

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

    async def test_accepts_csv_and_shows_preview(self, mock_message, mock_state):
        csv_data = (
            "first_name,last_name,company_name,position,city,industry,telegram_user_id,telegram_username,phone\n"
            "Alice,Lead,Acme,CEO,Moscow,SaaS,123,alice,+100\n"
            "Bob,Buyer,Beta,CTO,SPB,IT,456,bob,+200\n"
        ).encode()
        mock_message.document = MagicMock(file_name="leads.csv", file_id="file-1")
        bot = AsyncMock()
        bot.get_file.return_value = SimpleNamespace(file_path="tmp/leads.csv")
        bot.download_file.return_value = SimpleNamespace(read=lambda: csv_data)

        with patch("app.bots.admin_bot._get_bot", return_value=bot):
            await process_upload_file(mock_message, mock_state)

        mock_state.update_data.assert_awaited_once()
        records = mock_state.update_data.await_args.kwargs["records"]
        assert len(records) == 2
        assert records[0]["telegram_user_id"] == 123
        mock_state.set_state.assert_awaited_once_with(CSVImportFSM.preview)
        assert "Найдено 2 контактов" in mock_message.answer.call_args[0][0]

    async def test_accepts_excel_and_english_preview(self, mock_message, mock_state):
        mock_message.from_user.id = 905
        _admin_language_by_user[905] = LANG_EN
        mock_message.document = MagicMock(file_name="leads.xlsx", file_id="file-1")
        bot = AsyncMock()
        bot.get_file.return_value = SimpleNamespace(file_path="tmp/leads.xlsx")
        bot.download_file.return_value = SimpleNamespace(read=lambda: b"excel-bytes")
        records = [
            {
                "first_name": "Alice",
                "last_name": "Lead",
                "company_name": "Acme",
                "position": "CEO",
                "telegram_user_id": 123,
            }
        ]

        with (
            patch("app.bots.admin_bot._get_bot", return_value=bot),
            patch("app.services.contact_import.parse_excel", return_value=records),
        ):
            await process_upload_file(mock_message, mock_state)

        mock_state.update_data.assert_awaited_once_with(records=records)
        assert "Found 1 contacts" in mock_message.answer.call_args[0][0]

    async def test_parse_error_clears_state(self, mock_message, mock_state):
        mock_message.document = MagicMock(file_name="leads.csv", file_id="file-1")
        bot = AsyncMock()
        bot.get_file.return_value = SimpleNamespace(file_path="tmp/leads.csv")
        bot.download_file.return_value = SimpleNamespace(read=lambda: b"bad,data\n1,2")

        with patch("app.bots.admin_bot._get_bot", return_value=bot):
            await process_upload_file(mock_message, mock_state)

        mock_state.clear.assert_awaited_once()
        assert "Проверьте файл" in mock_message.answer.call_args[0][0]

    async def test_generic_parse_error_is_reported(self, mock_message, mock_state):
        mock_message.document = MagicMock(file_name="leads.csv", file_id="file-1")
        bot = AsyncMock()
        bot.get_file.return_value = SimpleNamespace(file_path="tmp/leads.csv")
        bot.download_file.return_value = SimpleNamespace(read=lambda: b"csv")

        with (
            patch("app.bots.admin_bot._get_bot", return_value=bot),
            patch(
                "app.services.contact_import.parse_csv",
                side_effect=ValueError("broken csv"),
            ),
        ):
            await process_upload_file(mock_message, mock_state)

        mock_state.clear.assert_awaited_once()
        assert "Ошибка парсинга" in mock_message.answer.call_args[0][0]

    async def test_cancel_csv_import(self, mock_callback, mock_state):
        await admin_bot_module.cancel_csv_import(mock_callback, mock_state)

        mock_state.clear.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("❌ Импорт отменен")
        mock_callback.message.answer.assert_awaited_once_with("Импорт отменен.")

    async def test_start_campaign_from_csv_opens_picker(self, mock_callback, mock_state):
        with patch(
            "app.bots.admin_bot._show_campaign_script_picker", new=AsyncMock()
        ) as picker:
            await admin_bot_module.start_campaign_from_csv(mock_callback, mock_state)

        picker.assert_awaited_once_with(mock_callback, mock_state)

    async def test_send_or_edit_callback_message_branches(self, mock_callback):
        result = await admin_bot_module._send_or_edit_callback_message(
            mock_callback, "Text"
        )
        assert result == "edited"
        mock_callback.message.edit_text.assert_awaited_once()

        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: message is not modified"
            )
        )
        result = await admin_bot_module._send_or_edit_callback_message(
            mock_callback, "Text"
        )
        assert result == "unchanged"

        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit"
            )
        )
        result = await admin_bot_module._send_or_edit_callback_message(
            mock_callback, "Text"
        )
        assert result == "sent"
        mock_callback.message.answer.assert_awaited()

        callback_without_message = SimpleNamespace(message=None)
        result = await admin_bot_module._send_or_edit_callback_message(
            callback_without_message, "Text"
        )
        assert result == "missing_message"

    async def test_show_campaign_script_picker_empty_missing_and_success(
        self, mock_callback, mock_state
    ):
        mock_state.get_data.return_value = {"records": []}
        await admin_bot_module._show_campaign_script_picker(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Нет контактов")
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        mock_state.get_data.return_value = {
            "records": [{"first_name": "Alice", "telegram_user_id": "123"}]
        }
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        context = _make_mock_session(result)
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock,
        ):
            await admin_bot_module._show_campaign_script_picker(mock_callback, mock_state)
        assert "Нет активных бизнесов" in send_mock.await_args.args[1]
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        script = Script(id=uuid.uuid4(), name="Cups", is_active=True)
        result.scalars.return_value.all.return_value = [script]
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.bots.admin_bot._send_or_edit_callback_message",
                new=AsyncMock(),
            ) as send_mock,
        ):
            await admin_bot_module._show_campaign_script_picker(mock_callback, mock_state)

        mock_state.set_state.assert_awaited_with(CampaignCreateFSM.select_script)
        keyboard = send_mock.await_args.kwargs["reply_markup"]
        assert keyboard.inline_keyboard[0][0].callback_data == f"campaign_script:{script.id}"
        mock_callback.answer.assert_awaited_once()


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


class TestDiscoverLeads:
    async def test_discover_wizard_prompts_each_step(self, mock_message, mock_state):
        await admin_bot_module.cmd_discover(mock_message, mock_state)
        mock_state.set_state.assert_awaited_with(admin_bot_module.DiscoverFSM.business_description)
        assert "Поиск лидов" in mock_message.answer.call_args[0][0]

        mock_message.answer.reset_mock()
        mock_message.text = "Custom cups"
        await admin_bot_module.process_discover_business(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(business_description="Custom cups")
        mock_state.set_state.assert_awaited_with(admin_bot_module.DiscoverFSM.audience_description)
        assert "целевую аудиторию" in mock_message.answer.call_args[0][0]

        mock_message.answer.reset_mock()
        mock_message.text = "Coffee shops"
        await admin_bot_module.process_discover_audience(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(audience_description="Coffee shops")
        mock_state.set_state.assert_awaited_with(admin_bot_module.DiscoverFSM.country)

        mock_message.answer.reset_mock()
        mock_message.text = "Poland"
        await admin_bot_module.process_discover_country(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(country="Poland")
        mock_state.set_state.assert_awaited_with(admin_bot_module.DiscoverFSM.language)

        mock_message.answer.reset_mock()
        mock_message.text = "Polish"
        await admin_bot_module.process_discover_language(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(language="Polish")
        mock_state.set_state.assert_awaited_with(admin_bot_module.DiscoverFSM.pain_keywords)

        mock_message.answer.reset_mock()
        mock_message.text = "-"
        await admin_bot_module.process_discover_pains(mock_message, mock_state)
        mock_state.update_data.assert_awaited_with(pain_keywords="")
        mock_state.set_state.assert_awaited_with(admin_bot_module.DiscoverFSM.limit)

    async def test_discover_start_english_prompt(self, mock_message, mock_state):
        mock_message.from_user.id = 907
        _admin_language_by_user[907] = LANG_EN

        await admin_bot_module.cmd_discover(mock_message, mock_state)

        assert "Lead search through Telegram" in mock_message.answer.call_args[0][0]

    async def test_discover_action_cancel_upload_and_unknown(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "discover_action:cancel"
        await admin_bot_module.process_discover_action(mock_callback, mock_state)
        mock_state.clear.assert_awaited_once()
        mock_callback.answer.assert_awaited_once_with("Отменено")

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        mock_callback.data = "discover_action:upload"
        with patch("app.bots.admin_bot.cmd_upload", new=AsyncMock()) as upload_mock:
            await admin_bot_module.process_discover_action(mock_callback, mock_state)
        mock_state.clear.assert_awaited_once()
        upload_mock.assert_awaited_once_with(mock_callback.message, mock_state)

        mock_callback.answer.reset_mock()
        mock_callback.data = "discover_action:noop"
        await admin_bot_module.process_discover_action(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once()

    async def test_discover_limit_reports_missing_telegram_config(
        self, mock_message, mock_state
    ):
        mock_message.text = "not a number"
        mock_state.get_data.return_value = {
            "business_description": "CRM",
            "audience_description": "Logistics owners",
            "country": "Poland",
            "language": "Polish",
            "pain_keywords": "crm",
        }

        with patch(
            "app.bots.admin_bot._start_discovery_seller_client",
            new=AsyncMock(return_value=(None, None, "telegram_api_missing")),
        ):
            await admin_bot_module.process_discover_limit(mock_message, mock_state)

        mock_state.update_data.assert_awaited_with(limit=20)
        assert "TELEGRAM_API_ID" in mock_message.answer.call_args[0][0]
        mock_state.clear.assert_awaited_once()

    async def test_discover_limit_success_sends_csv_and_summary(
        self, mock_message, mock_state
    ):
        mock_message.text = "5"
        mock_state.get_data.return_value = {
            "business_description": "Custom cups",
            "audience_description": "Coffee shop owners",
            "country": "Poland",
            "language": "Polish",
            "pain_keywords": "cups",
        }
        seller_client = AsyncMock()
        search_result = SimpleNamespace(
            records=[
                {
                    "first_name": "Anna",
                    "last_name": "Lead",
                    "telegram_user_id": "123",
                    "telegram_username": "anna",
                    "source_summary": "Asked for branded cups",
                }
            ],
            queries=["kubki kawa"],
            groups=["chat"],
            errors=[],
            posts_checked=12,
        )
        searcher = AsyncMock()
        searcher.run.return_value = search_result

        with (
            patch(
                "app.bots.admin_bot._start_discovery_seller_client",
                new=AsyncMock(return_value=("telegram-client", seller_client, None)),
            ),
            patch(
                "app.services.telegram_global_lead_search.TelegramGlobalLeadSearch",
                return_value=searcher,
            ),
            patch("app.bots.admin_bot._send_discovery_csv", new=AsyncMock()) as csv_mock,
        ):
            await admin_bot_module.process_discover_limit(mock_message, mock_state)

        csv_mock.assert_awaited_once()
        seller_client.stop.assert_awaited_once()
        mock_state.set_state.assert_awaited_with(admin_bot_module.DiscoverFSM.confirm)
        assert "Готово. CSV отправлен" in mock_message.answer.call_args[0][0]

    async def test_discover_limit_english_success_summary(
        self, mock_message, mock_state
    ):
        mock_message.from_user.id = 908
        _admin_language_by_user[908] = LANG_EN
        mock_message.text = "5"
        mock_state.get_data.return_value = {
            "business_description": "Custom cups",
            "audience_description": "Coffee shop owners",
            "country": "Poland",
            "language": "Polish",
            "pain_keywords": "cups",
        }
        seller_client = AsyncMock()
        search_result = SimpleNamespace(
            records=[],
            queries=["cups"],
            groups=[],
            errors=[],
            posts_checked=0,
        )
        searcher = AsyncMock()
        searcher.run.return_value = search_result

        with (
            patch(
                "app.bots.admin_bot._start_discovery_seller_client",
                new=AsyncMock(return_value=("telegram-client", seller_client, None)),
            ),
            patch(
                "app.services.telegram_global_lead_search.TelegramGlobalLeadSearch",
                return_value=searcher,
            ),
            patch("app.bots.admin_bot._send_discovery_csv", new=AsyncMock()),
        ):
            await admin_bot_module.process_discover_limit(mock_message, mock_state)

        text = mock_message.answer.call_args[0][0]
        assert "Done. CSV sent" in text
        assert "Add and create launch" in mock_message.answer.call_args.kwargs[
            "reply_markup"
        ].inline_keyboard[0][0].text

    async def test_discover_limit_search_error_stops_client(
        self, mock_message, mock_state
    ):
        mock_message.text = "10"
        mock_state.get_data.return_value = {
            "business_description": "Custom cups",
            "audience_description": "Coffee shop owners",
            "country": "Poland",
            "language": "Polish",
            "pain_keywords": "cups",
        }
        seller_client = AsyncMock()
        searcher = AsyncMock()
        searcher.run.side_effect = RuntimeError("search down")

        with (
            patch(
                "app.bots.admin_bot._start_discovery_seller_client",
                new=AsyncMock(return_value=("telegram-client", seller_client, None)),
            ),
            patch(
                "app.services.telegram_global_lead_search.TelegramGlobalLeadSearch",
                return_value=searcher,
            ),
        ):
            await admin_bot_module.process_discover_limit(mock_message, mock_state)

        seller_client.stop.assert_awaited_once()
        mock_state.clear.assert_awaited_once()
        assert "Ошибка при поиске" in mock_message.answer.call_args[0][0]

    async def test_discover_confirm_preview_csv_cancel_add_and_error(
        self, mock_callback, mock_state
    ):
        discovered = [
            {
                "first_name": "Anna",
                "last_name": "Lead",
                "telegram_user_id": "123",
                "telegram_username": "anna",
                "source_summary": "Asked for cups",
                "source_url": "https://t.me/c/1/2",
            }
        ]
        mock_state.get_data.return_value = {
            "discovered": discovered,
            "source": "telegram_search",
        }

        mock_callback.data = "discover_confirm:preview"
        await admin_bot_module.process_discover_confirm(mock_callback, mock_state)
        assert "Полный список" in mock_callback.message.answer.call_args[0][0]

        mock_callback.answer.reset_mock()
        mock_callback.message.answer.reset_mock()
        mock_callback.data = "discover_confirm:csv"
        with patch("app.bots.admin_bot._send_discovery_csv", new=AsyncMock()) as csv_mock:
            await admin_bot_module.process_discover_confirm(mock_callback, mock_state)
        csv_mock.assert_awaited_once_with(mock_callback.message, discovered, "ru")
        mock_callback.answer.assert_awaited_once_with("CSV отправлен")

        mock_callback.answer.reset_mock()
        mock_callback.message.answer.reset_mock()
        mock_callback.data = "discover_confirm:add"
        created = [Contact(id=uuid.uuid4(), telegram_user_id=123)]
        context = _make_mock_session(MagicMock())
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.services.contact_import.upsert_contacts",
                new=AsyncMock(return_value=(created, [])),
            ),
            patch(
                "app.bots.admin_bot.start_campaign_from_csv", new=AsyncMock()
            ) as start_mock,
        ):
            await admin_bot_module.process_discover_confirm(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("✅ Добавлено!")
        start_mock.assert_awaited_once_with(mock_callback, mock_state)

        mock_callback.answer.reset_mock()
        mock_callback.message.answer.reset_mock()
        mock_callback.data = "discover_confirm:add"
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.services.contact_import.upsert_contacts",
                new=AsyncMock(side_effect=RuntimeError("db down")),
            ),
        ):
            await admin_bot_module.process_discover_confirm(mock_callback, mock_state)
        mock_state.clear.assert_awaited()
        mock_callback.answer.assert_awaited_once_with("❌ Ошибка")
        assert "Ошибка сохранения" in mock_callback.message.answer.call_args[0][0]

        mock_callback.answer.reset_mock()
        mock_callback.message.answer.reset_mock()
        mock_callback.data = "discover_confirm:cancel"
        await admin_bot_module.process_discover_confirm(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Отменено")

        mock_callback.answer.reset_mock()
        mock_callback.data = "discover_confirm:unknown"
        await admin_bot_module.process_discover_confirm(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once()

    async def test_discovery_csv_helpers_send_document(self, mock_message):
        mock_message.chat = MagicMock(id=777)
        records = [{"first_name": "Anna", "telegram_user_id": "123"}]
        csv_bytes = admin_bot_module._discovery_csv_bytes(records)
        assert b"telegram_user_id" in csv_bytes
        bot = AsyncMock()

        with patch("app.bots.admin_bot._get_bot", return_value=bot):
            await admin_bot_module._send_discovery_csv(mock_message, records)

        bot.send_document.assert_awaited_once()
        assert bot.send_document.await_args.kwargs["chat_id"] == 777
        assert bot.send_document.await_args.kwargs["document"].filename == "telegram_leads.csv"

    async def test_discovery_config_texts_and_seller_client_startup(self):
        assert "Внешний поиск лидов" in admin_bot_module._discovery_config_error_text(
            None, "external_api"
        )
        assert "ready/active" in admin_bot_module._discovery_config_error_text(
            "telegram_account_missing", "telegram_search"
        )
        assert "Клиент Telegram" in admin_bot_module._discovery_config_error_text(
            "telegram_client_failed", "telegram_search"
        )
        assert "Для поиска лидов" in admin_bot_module._telegram_search_missing_text()

        client, seller, error = await admin_bot_module._start_discovery_seller_client(
            "external_api"
        )
        assert (client, seller, error) == (None, None, None)

        with patch(
            "app.bots.admin_bot.get_settings",
            return_value=SimpleNamespace(telegram_api_id=None, telegram_api_hash=None),
        ):
            client, seller, error = await admin_bot_module._start_discovery_seller_client(
                "telegram_search"
            )
        assert error == "telegram_api_missing"

        no_account_result = MagicMock()
        no_account_result.scalar_one_or_none.return_value = None
        with (
            patch(
                "app.bots.admin_bot.get_settings",
                return_value=SimpleNamespace(telegram_api_id=1, telegram_api_hash="hash"),
            ),
            patch(
                "app.bots.admin_bot.AsyncSessionLocal",
                return_value=_make_mock_session(no_account_result),
            ),
        ):
            client, seller, error = await admin_bot_module._start_discovery_seller_client(
                "telegram_search"
            )
        assert error == "telegram_account_missing"

        account = SimpleNamespace(
            id=uuid.uuid4(),
            session_string="session",
            proxy_url=None,
        )
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account
        context = _make_mock_session(account_result)

        failing_seller = AsyncMock()
        failing_seller.start = AsyncMock(side_effect=RuntimeError("bad session"))
        failing_seller.stop = AsyncMock()
        with (
            patch(
                "app.bots.admin_bot.get_settings",
                return_value=SimpleNamespace(telegram_api_id=1, telegram_api_hash="hash"),
            ),
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.seller_client.SellerClient", return_value=failing_seller),
        ):
            client, seller, error = await admin_bot_module._start_discovery_seller_client(
                "telegram_search"
            )
        assert error == "telegram_client_failed"
        failing_seller.stop.assert_awaited_once()

        no_client_seller = AsyncMock()
        no_client_seller.start = AsyncMock()
        no_client_seller.stop = AsyncMock()
        no_client_seller._client = None
        with (
            patch(
                "app.bots.admin_bot.get_settings",
                return_value=SimpleNamespace(telegram_api_id=1, telegram_api_hash="hash"),
            ),
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.seller_client.SellerClient", return_value=no_client_seller),
        ):
            client, seller, error = await admin_bot_module._start_discovery_seller_client(
                "telegram_search"
            )
        assert error == "telegram_client_failed"
        no_client_seller.stop.assert_awaited_once()

        ok_seller = AsyncMock()
        ok_seller.start = AsyncMock()
        ok_seller._client = "client"
        with (
            patch(
                "app.bots.admin_bot.get_settings",
                return_value=SimpleNamespace(telegram_api_id=1, telegram_api_hash="hash"),
            ),
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.seller_client.SellerClient", return_value=ok_seller),
        ):
            client, seller, error = await admin_bot_module._start_discovery_seller_client(
                "telegram_search"
            )
        assert (client, seller, error) == ("client", ok_seller, None)


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

    async def test_rejects_non_draft_campaign(self, mock_callback, mock_state):
        campaign = Campaign(id=uuid.uuid4(), name="Running", status="running")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = campaign
        context = _make_mock_session(result_mock)
        mock_callback.data = f"startcamp:{campaign.id}"

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_startcamp(mock_callback, mock_state)

        mock_callback.answer.assert_awaited_once_with("❌ Этот запуск уже не черновик")
        mock_state.clear.assert_awaited_once()

    async def test_starts_draft_and_reports_scheduler_result(
        self, mock_callback, mock_state
    ):
        script_id = uuid.uuid4()
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Draft",
            status="draft",
            script_id=script_id,
            total_contacts=3,
        )
        script = Script(
            id=script_id,
            name="Biz",
            working_hours_start=dt_time(0, 0),
            working_hours_end=dt_time(23, 59),
            timezone="UTC",
        )
        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = script
        session = AsyncMock()
        session.execute.side_effect = [campaign_result, script_result]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)
        mock_callback.data = f"startcamp:{campaign.id}"

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.core.scheduler.process_campaigns", new=AsyncMock()),
        ):
            await handle_startcamp(mock_callback, mock_state)

        assert campaign.status == "running"
        mock_callback.answer.assert_awaited_once_with("✅ Запуск начат!")
        assert "В очереди 3 контакта" in mock_callback.message.answer.call_args[0][0]

    async def test_starts_draft_even_when_immediate_processing_fails(
        self, mock_callback, mock_state
    ):
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Draft",
            status="draft",
            total_contacts=1,
        )
        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.side_effect = [campaign_result, script_result]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)
        mock_callback.data = f"startcamp:{campaign.id}"

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.core.scheduler.process_campaigns",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
        ):
            await handle_startcamp(mock_callback, mock_state)

        assert campaign.status == "running"
        mock_callback.answer.assert_awaited_once_with(
            "⚠️ Запуск начат, отправка будет повторена"
        )
        assert "повторит обработку" in mock_callback.message.answer.call_args[0][0]


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

    async def test_select_script_multi_contact_preview_offers_show_all(
        self, mock_callback, mock_state
    ):
        script_id = uuid.uuid4()
        mock_callback.data = f"campaign_script:{script_id}"
        mock_state.get_data.return_value = {
            "records": [
                {"first_name": "Alice", "telegram_user_id": "123"},
                {"first_name": "Bob", "telegram_user_id": "456"},
            ],
        }
        script = Script(id=script_id, name="Test Script", goal="Book")
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

        text = mock_callback.message.edit_text.call_args[0][0]
        keyboard = mock_callback.message.edit_text.call_args.kwargs["reply_markup"]
        assert "1 из 2" in text
        assert "Показать все 2" in keyboard.inline_keyboard[1][0].text
        assert keyboard.inline_keyboard[1][0].callback_data == "preview:show_all"

    async def test_select_script_invalid_no_records_and_missing_script(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "campaign_script:not-a-uuid"
        await process_campaign_script(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID бизнеса")
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        mock_callback.data = f"campaign_script:{uuid.uuid4()}"
        mock_state.get_data.return_value = {"records": []}
        await process_campaign_script(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Нет контактов")
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        context = _make_mock_session(result)
        mock_state.get_data.return_value = {
            "records": [{"first_name": "Alice", "telegram_user_id": "123"}]
        }
        mock_callback.data = f"campaign_script:{uuid.uuid4()}"
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await process_campaign_script(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")
        mock_state.clear.assert_awaited_once()

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

    async def test_preview_regenerate_reraises_real_edit_error(
        self, mock_callback, mock_state
    ):
        script_id = uuid.uuid4()
        mock_callback.data = "preview:regenerate"
        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit"
            )
        )
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "records": [{"first_name": "Bob", "telegram_user_id": "456"}],
        }
        script = Script(id=script_id, name="Test Script", goal="Book")
        result = MagicMock()
        result.scalar_one_or_none.return_value = script
        context = _make_mock_session(result)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.bots.admin_bot._generate_preview_message",
                new=AsyncMock(return_value="New"),
            ),
            pytest.raises(TelegramBadRequest),
        ):
            await handle_preview_regenerate(mock_callback, mock_state)

    async def test_preview_regenerate_session_expired_and_script_missing(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "preview:regenerate"
        mock_state.get_data.return_value = {"records": []}
        await handle_preview_regenerate(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Сессия устарела")
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        script_id = uuid.uuid4()
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "records": [{"first_name": "Bob", "telegram_user_id": "456"}],
        }
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        context = _make_mock_session(result)
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_preview_regenerate(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")
        mock_state.clear.assert_awaited_once()

    async def test_preview_show_all_generates_every_contact(
        self, mock_callback, mock_state
    ):
        script_id = uuid.uuid4()
        mock_callback.data = "preview:show_all"
        records = [
            {
                "first_name": "Alice",
                "company_name": "Acme",
                "telegram_user_id": "123",
            },
            {
                "first_name": "Bob",
                "company_name": "Beta",
                "telegram_user_id": "456",
            },
        ]
        mock_state.get_data.return_value = {"script_id": script_id, "records": records}
        script = Script(id=script_id, name="Test Script", goal="Book")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = script
        context = _make_mock_session(result_mock)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.bots.admin_bot._generate_preview_message",
                new=AsyncMock(side_effect=["Привет Alice", "Привет Bob"]),
            ) as generate_mock,
        ):
            await handle_preview_show_all(mock_callback, mock_state)

        assert generate_mock.await_count == 2
        mock_state.update_data.assert_awaited_with(
            preview_messages=["Привет Alice", "Привет Bob"]
        )
        text = mock_callback.message.edit_text.call_args[0][0]
        keyboard = mock_callback.message.edit_text.call_args.kwargs["reply_markup"]
        assert "Сгенерированные первые сообщения (2)" in text
        assert "Alice" in text
        assert "Привет Bob" in text
        assert keyboard.inline_keyboard[1][0].callback_data == "preview:show_first"

    async def test_preview_show_all_session_expired_missing_script_and_long_chunks(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "preview:show_all"
        mock_state.get_data.return_value = {"records": []}
        await handle_preview_show_all(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Сессия устарела")
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        script_id = uuid.uuid4()
        records = [{"first_name": "Alice", "telegram_user_id": "123"}]
        mock_state.get_data.return_value = {"script_id": script_id, "records": records}
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        context = _make_mock_session(result)
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await handle_preview_show_all(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Бизнес не найден")
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        script = Script(id=script_id, name="Test Script", goal="Book")
        result.scalar_one_or_none.return_value = script
        long_records = [
            {"first_name": "Alice", "telegram_user_id": "123"},
            {"first_name": "Bob", "telegram_user_id": "456"},
        ]
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "records": long_records,
        }
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.bots.admin_bot._generate_preview_message",
                new=AsyncMock(side_effect=["A" * 3900, "B" * 3900]),
            ),
        ):
            await handle_preview_show_all(mock_callback, mock_state)

        assert mock_callback.message.answer.await_count >= 2

    async def test_preview_show_all_reraises_real_edit_error(
        self, mock_callback, mock_state
    ):
        script_id = uuid.uuid4()
        mock_callback.data = "preview:show_all"
        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit"
            )
        )
        records = [{"first_name": "Alice", "telegram_user_id": "123"}]
        mock_state.get_data.return_value = {"script_id": script_id, "records": records}
        result = MagicMock()
        result.scalar_one_or_none.return_value = Script(
            id=script_id, name="Test Script", goal="Book"
        )
        context = _make_mock_session(result)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.bots.admin_bot._generate_preview_message",
                new=AsyncMock(return_value="Hello"),
            ),
            pytest.raises(TelegramBadRequest),
        ):
            await handle_preview_show_all(mock_callback, mock_state)

    async def test_preview_show_first_restores_sample(self, mock_callback, mock_state):
        mock_callback.data = "preview:show_first"
        mock_state.get_data.return_value = {
            "preview_text": "Привет, Alice",
            "records": [
                {"first_name": "Alice", "telegram_user_id": "123"},
                {"first_name": "Bob", "telegram_user_id": "456"},
            ],
        }

        await handle_preview_show_first(mock_callback, mock_state)

        text = mock_callback.message.edit_text.call_args[0][0]
        keyboard = mock_callback.message.edit_text.call_args.kwargs["reply_markup"]
        assert "1 из 2" in text
        assert "Привет, Alice" in text
        assert keyboard.inline_keyboard[1][0].callback_data == "preview:show_all"
        mock_callback.answer.assert_awaited_once()

    async def test_preview_show_first_session_expired_and_not_modified(
        self, mock_callback, mock_state
    ):
        mock_callback.data = "preview:show_first"
        mock_state.get_data.return_value = {"records": []}
        await handle_preview_show_first(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("❌ Сессия устарела")
        mock_state.clear.assert_awaited_once()

        mock_callback.answer.reset_mock()
        mock_state.clear.reset_mock()
        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: message is not modified"
            )
        )
        mock_state.get_data.return_value = {
            "preview_text": "Hello",
            "records": [{"first_name": "Alice", "telegram_user_id": "123"}],
        }
        await handle_preview_show_first(mock_callback, mock_state)
        mock_callback.answer.assert_awaited_once_with("Без изменений")

        mock_callback.answer.reset_mock()
        mock_callback.message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit"
            )
        )
        with pytest.raises(TelegramBadRequest):
            await handle_preview_show_first(mock_callback, mock_state)

    async def test_process_campaign_name_cancel_and_create_paths(
        self, mock_message, mock_callback, mock_state
    ):
        script_id = uuid.uuid4()
        script = Script(id=script_id, name="Biz")
        result = MagicMock()
        result.scalar_one_or_none.return_value = script
        context = _make_mock_session(result)
        mock_message.text = "July Launch"
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "records": [{"first_name": "Alice", "telegram_user_id": "123"}],
            "campaign_name": "July Launch",
            "preview_text": "Hi Alice",
        }
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await admin_bot_module.process_campaign_name(mock_message, mock_state)

        mock_state.update_data.assert_awaited_with(campaign_name="July Launch")
        mock_state.set_state.assert_awaited_with(CampaignCreateFSM.confirm)
        assert "Сводка перед запуском" in mock_message.answer.call_args[0][0]

        await admin_bot_module.cancel_campaign_create(mock_callback, mock_state)
        mock_state.clear.assert_awaited()
        mock_callback.answer.assert_awaited_with("❌ Создание отменено")

    async def test_process_campaign_name_english_review(self, mock_message, mock_state):
        user_id = 906
        mock_message.from_user.id = user_id
        _admin_language_by_user[user_id] = LANG_EN
        script_id = uuid.uuid4()
        result = MagicMock()
        result.scalar_one_or_none.return_value = Script(id=script_id, name="Biz")
        context = _make_mock_session(result)
        mock_message.text = "July Launch"
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "records": [{"first_name": "Alice", "telegram_user_id": "123"}],
            "campaign_name": "July Launch",
            "preview_text": "Hi Alice",
        }

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await admin_bot_module.process_campaign_name(mock_message, mock_state)

        text = mock_message.answer.call_args[0][0]
        assert "Launch review" in text
        assert "Start now?" in text

    def test_preview_text_and_record_label_english_branches(self):
        assert "1 of 2" in _format_preview_text("Hello", 2, LANG_EN)
        assert admin_bot_module._preview_record_label({}, 3, LANG_EN) == "Contact 3"

    async def test_campaign_start_later_and_now_create_contacts(
        self, mock_callback, mock_state
    ):
        records = [
            {"first_name": "Alice", "telegram_user_id": "123"},
            {"first_name": "Bob", "telegram_user_id": "456"},
        ]
        contacts = [
            Contact(id=uuid.uuid4(), first_name="Alice", telegram_user_id=123),
            Contact(id=uuid.uuid4(), first_name="Bob", telegram_user_id=456),
        ]
        script_id = uuid.uuid4()
        mock_state.get_data.return_value = {
            "script_id": script_id,
            "campaign_name": "Launch",
            "records": records,
        }
        session = AsyncMock()
        session.add = MagicMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.services.contact_import.upsert_contacts",
                new=AsyncMock(return_value=(contacts, [])),
            ),
            patch(
                "app.services.contact_import.contacts_in_record_order",
                return_value=contacts,
            ),
        ):
            await admin_bot_module.campaign_start_later(mock_callback, mock_state)

        mock_state.clear.assert_awaited()
        mock_callback.answer.assert_awaited_with("✅ Черновик сохранен")
        added_contacts = [
            call.args[0]
            for call in session.add.call_args_list
            if isinstance(call.args[0], admin_bot_module.CampaignContact)
        ]
        assert [cc.queue_position for cc in added_contacts] == [1, 2]

        mock_callback.answer.reset_mock()
        mock_callback.message.answer.reset_mock()
        session.add.reset_mock()
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = Script(
            id=script_id,
            name="Biz",
            working_hours_start=dt_time(0, 0),
            working_hours_end=dt_time(23, 59),
            timezone="UTC",
        )
        session.execute.return_value = script_result
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch(
                "app.services.contact_import.upsert_contacts",
                new=AsyncMock(return_value=(contacts, [])),
            ),
            patch(
                "app.services.contact_import.contacts_in_record_order",
                return_value=contacts,
            ),
            patch("app.bots.admin_bot._schedule_process_campaign") as schedule,
        ):
            await admin_bot_module.campaign_start_now(mock_callback, mock_state)

        schedule.assert_called_once()
        mock_callback.answer.assert_awaited_with("✅ Запуск начат!")
        assert "начат с 2 контактами" in mock_callback.message.answer.call_args[0][0]

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

    async def test_preview_retries_when_initial_message_needs_fix(self):
        script = Script(id=uuid.uuid4(), name="Test Script", goal="Book")
        mock_engine = MagicMock()
        mock_engine.generate_response_with_guardrails = AsyncMock(
            side_effect=[
                {"text": "Bad first", "model": "openai"},
                {"text": "Good retry", "model": "openai"},
            ]
        )

        with (
            patch("app.bots.admin_bot.LLMEngine", return_value=mock_engine),
            patch(
                "app.bots.admin_bot.needs_initial_message_retry",
                side_effect=[True, False],
            ),
        ):
            text = await _generate_preview_message(
                script,
                {"first_name": "Максим", "telegram_user_id": "123"},
            )

        assert text == "Good retry"
        assert mock_engine.generate_response_with_guardrails.await_count == 2

    async def test_preview_retry_falls_back_when_retry_is_bad_or_exception(self):
        script = Script(id=uuid.uuid4(), name="Test Script", goal="Book")
        mock_engine = MagicMock()
        mock_engine.generate_response_with_guardrails = AsyncMock(
            side_effect=[
                {"text": "Bad first", "model": "openai"},
                {"text": "Still bad", "model": "fallback"},
            ]
        )

        with (
            patch("app.bots.admin_bot.LLMEngine", return_value=mock_engine),
            patch("app.bots.admin_bot.needs_initial_message_retry", return_value=True),
        ):
            text = await _generate_preview_message(
                script,
                {"first_name": "Максим", "telegram_user_id": "123"},
            )
        assert "Привет, Максим" in text

        mock_engine.generate_response_with_guardrails = AsyncMock(
            side_effect=RuntimeError("llm down")
        )
        with patch("app.bots.admin_bot.LLMEngine", return_value=mock_engine):
            text = await _generate_preview_message(
                script,
                {"first_name": "Максим", "telegram_user_id": "123"},
            )
        assert "Привет, Максим" in text

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


class TestBackgroundCampaignProcessing:
    async def test_schedule_process_campaign_uses_create_task(self):
        campaign_id = uuid.uuid4()
        task = object()
        process = AsyncMock()

        with patch("app.bots.admin_bot.asyncio.create_task", return_value=task) as create_task:
            result = admin_bot_module._schedule_process_campaign(campaign_id, process)

        assert result is task
        create_task.assert_called_once()
        create_task.call_args.args[0].close()

    async def test_process_campaign_safely_runs_and_logs_errors(self):
        process = AsyncMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value="session")
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await admin_bot_module._process_campaign_safely(uuid.uuid4(), process)

        process.assert_awaited_once_with("session")

        process = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await admin_bot_module._process_campaign_safely(uuid.uuid4(), process)

        process.assert_awaited_once_with("session")


class TestSendOrEditCampaigns:
    @pytest.mark.asyncio
    async def test_empty_campaigns_and_not_modified_edit(self, mock_message):
        with patch("app.bots.admin_bot._load_campaigns", new=AsyncMock(return_value=[])):
            await _send_or_edit_campaigns(mock_message)
        assert "Запусков пока нет" in mock_message.answer.call_args[0][0]

        mock_message.answer.reset_mock()
        mock_message.from_user.is_bot = True
        mock_message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(),
                message="Bad Request: message is not modified",
            )
        )
        with patch("app.bots.admin_bot._load_campaigns", new=AsyncMock(return_value=[])):
            await _send_or_edit_campaigns(mock_message)
        mock_message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_campaigns_reraises_real_edit_error(self, mock_message):
        mock_message.from_user.is_bot = True
        mock_message.edit_text = AsyncMock(
            side_effect=TelegramBadRequest(
                method=MagicMock(), message="Bad Request: cannot edit"
            )
        )

        with (
            patch("app.bots.admin_bot._load_campaigns", new=AsyncMock(return_value=[])),
            pytest.raises(TelegramBadRequest),
        ):
            await _send_or_edit_campaigns(mock_message)

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
    async def test_campaign_pause_resume_invalid_and_unavailable(self, mock_callback):
        for handler, prefix in (
            (handle_camp_pause, "camp_pause"),
            (handle_camp_resume, "camp_resume"),
        ):
            mock_callback.answer.reset_mock()
            mock_callback.data = f"{prefix}:bad"
            await handler(mock_callback)
            mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

        not_running = Campaign(id=uuid.uuid4(), name="Draft", status="draft")
        result = MagicMock()
        result.scalar_one_or_none.return_value = not_running
        context = _make_mock_session(result)
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.answer.reset_mock()
            mock_callback.data = f"camp_pause:{not_running.id}"
            await handle_camp_pause(mock_callback)
            mock_callback.answer.assert_awaited_once_with("❌ Нельзя поставить на паузу")

        not_paused = Campaign(id=uuid.uuid4(), name="Running", status="running")
        result.scalar_one_or_none.return_value = not_paused
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.answer.reset_mock()
            mock_callback.data = f"camp_resume:{not_paused.id}"
            await handle_camp_resume(mock_callback)
            mock_callback.answer.assert_awaited_once_with("❌ Нельзя возобновить")

    @pytest.mark.asyncio
    async def test_campaign_pause_resume_success(self, mock_callback):
        running = Campaign(id=uuid.uuid4(), name="Run", status="running")
        result = MagicMock()
        result.scalar_one_or_none.return_value = running
        context = _make_mock_session(result)
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_pause:{running.id}"
            await handle_camp_pause(mock_callback)
        assert running.status == "paused"
        mock_callback.answer.assert_awaited_once_with("⏸ Пауза")

        mock_callback.answer.reset_mock()
        paused = Campaign(id=uuid.uuid4(), name="Pause", status="paused")
        result.scalar_one_or_none.return_value = paused
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_resume:{paused.id}"
            await handle_camp_resume(mock_callback)
        assert paused.status == "running"
        mock_callback.answer.assert_awaited_once_with("▶️ Возобновлено")

    @pytest.mark.asyncio
    async def test_campaign_start_invalid_and_already_started(self, mock_callback):
        mock_callback.data = "camp_start:bad"
        await handle_camp_start(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

        mock_callback.answer.reset_mock()
        campaign = Campaign(id=uuid.uuid4(), name="Started", status="running")
        result = MagicMock()
        result.scalar_one_or_none.return_value = campaign
        context = _make_mock_session(result)
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_start:{campaign.id}"
            await handle_camp_start(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Запуск уже начат или не найден")

    @pytest.mark.asyncio
    async def test_campaign_start_sends_queue_notice_when_contacts_exist(
        self, mock_callback
    ):
        script_id = uuid.uuid4()
        campaign = Campaign(
            id=uuid.uuid4(),
            name="Draft",
            status="draft",
            script_id=script_id,
            total_contacts=2,
        )
        script = Script(
            id=script_id,
            name="Biz",
            working_hours_start=dt_time(0, 0),
            working_hours_end=dt_time(23, 59),
            timezone="Europe/Moscow",
        )
        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign
        script_result = MagicMock()
        script_result.scalar_one_or_none.return_value = script
        session = AsyncMock()
        session.execute.side_effect = [campaign_result, script_result]
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
            patch("app.bots.admin_bot._schedule_process_campaign") as schedule,
        ):
            mock_callback.data = f"camp_start:{campaign.id}"
            await handle_camp_start(mock_callback)

        schedule.assert_called_once()
        mock_callback.message.answer.assert_awaited_once()
        assert "В очереди 2 контакта" in mock_callback.message.answer.call_args[0][0]

    @pytest.mark.asyncio
    async def test_campaign_delete_invalid_missing_and_with_conversations(
        self, mock_callback
    ):
        mock_callback.data = "camp_delete:bad"
        await handle_camp_delete(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID")

        mock_callback.answer.reset_mock()
        campaign_id = uuid.uuid4()
        missing_result = MagicMock()
        missing_result.scalar_one_or_none.return_value = None
        context = _make_mock_session(missing_result)
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_delete:{campaign_id}"
            await handle_camp_delete(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Запуск не найден")

        mock_callback.answer.reset_mock()
        campaign = Campaign(id=uuid.uuid4(), name="Delete", status="draft")
        campaign_result = MagicMock()
        campaign_result.scalar_one_or_none.return_value = campaign
        conv_result = MagicMock()
        conv_id = uuid.uuid4()
        conv_result.all.return_value = [(conv_id,)]
        session = AsyncMock()
        session.execute.side_effect = [campaign_result, conv_result, MagicMock(), MagicMock(), MagicMock()]
        session.delete = AsyncMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)
        with (
            patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context),
            patch("app.bots.admin_bot._send_or_edit_campaigns", new=AsyncMock()),
        ):
            mock_callback.data = f"camp_delete:{campaign.id}"
            await handle_camp_delete(mock_callback)
        session.delete.assert_awaited_once_with(campaign)
        mock_callback.answer.assert_awaited_once_with("🗑 Удалено")

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
