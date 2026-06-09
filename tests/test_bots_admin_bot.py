import uuid
from datetime import datetime, time as dt_time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import types
from aiogram.fsm.context import FSMContext

from app.bots.admin_bot import (
    _format_scripts,
    _format_campaigns,
    _format_hotleads,
    _format_analytics,
    cmd_start,
    cmd_scripts,
    cmd_campaigns,
    cmd_analytics,
    cmd_hotleads,
    cmd_conversations,
    handle_qualify,
    handle_reject,
    handle_dialog,
    start_bot,
    stop_bot,
    cmd_newscript,
    process_script_name,
    process_script_role,
    process_script_audience,
    process_script_goal,
    process_script_criteria,
    process_script_max_messages,
    process_script_delay,
    process_script_timezone,
    confirm_create_script,
    cancel_create_script,
    cmd_upload,
    process_upload_file,
    cmd_startcampaign,
    handle_startcamp,
    process_script_tone,
    process_work_hours_default,
    process_work_hours_manual,
    process_campaign_script,
    ScriptCreateFSM,
    CSVImportFSM,
    CampaignStartFSM,
    CampaignCreateFSM,
    DiscoverFSM,
)
from app.models import Script, Campaign, Conversation, Contact, Message


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


class TestFormatAnalytics:
    def test_analytics_output(self):
        text = _format_analytics(150, 142, 18, 3, 1)
        assert "Всего контактов: 150" in text
        assert "Отправлено: 142" in text
        assert "Ответили: 18 (12.7%)" in text
        assert "Hot leads: 3" in text
        assert "Встречи: 1" in text


class TestCmdStart:
    async def test_sends_welcome(self, mock_message):
        await cmd_start(mock_message)
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Welcome to AI Sales Manager Admin Bot" in text
        assert "/scripts" in text
        assert "/newscript" in text
        assert "/upload" in text
        assert "/startcampaign" in text


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
        session.scalar.side_effect = [150, 142, 18, 3, 1]
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


class TestCmdConversations:
    async def test_missing_args(self, mock_message):
        mock_message.text = "/conversations"
        await cmd_conversations(mock_message)
        mock_message.answer.assert_called_once_with("Usage: /conversations <contact_id>")

    async def test_invalid_uuid(self, mock_message):
        mock_message.text = "/conversations invalid"
        await cmd_conversations(mock_message)
        mock_message.answer.assert_called_once_with("Неверный формат contact_id. Ожидается UUID.")

    async def test_conversation_not_found(self, mock_message):
        mock_message.text = f"/conversations {uuid.uuid4()}"
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once_with("Диалог для данного контакта не найден.")

    async def test_returns_messages(self, mock_message):
        contact_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        mock_message.text = f"/conversations {contact_id}"

        conv = Conversation(id=conv_id, contact_id=contact_id, current_state="hot")
        msg = Message(id=uuid.uuid4(), conversation_id=conv_id, direction="inbound", content="Hello")

        session = AsyncMock()
        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = conv
        result2 = MagicMock()
        result2.scalars.return_value.all.return_value = [msg]
        session.execute.side_effect = [result1, result2]

        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_conversations(mock_message)

        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0]
        assert "Hello" in text

    async def test_no_messages(self, mock_message):
        contact_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        mock_message.text = f"/conversations {contact_id}"

        conv = Conversation(id=conv_id, contact_id=contact_id, current_state="hot")

        session = AsyncMock()
        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = conv
        result2 = MagicMock()
        result2.scalars.return_value.all.return_value = []
        session.execute.side_effect = [result1, result2]

        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=session)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
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
        mock_callback.answer.assert_awaited_once_with("✅ Статус обновлен: Qualified")

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
        mock_callback.answer.assert_awaited_once_with("❌ Статус обновлен: Rejected")

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
        msg1 = Message(id=uuid.uuid4(), conversation_id=conv_id, direction="outbound", content="Hello")
        msg2 = Message(id=uuid.uuid4(), conversation_id=conv_id, direction="inbound", content="Hi there")
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

        mock_callback.message.answer.assert_called_once_with("Сообщений в диалоге не найдено.")
        mock_callback.answer.assert_awaited_once()

    async def test_invalid_uuid(self, mock_callback):
        mock_callback.data = "dialog:invalid"
        await handle_dialog(mock_callback)
        mock_callback.answer.assert_awaited_once_with("❌ Неверный ID диалога")


# ---------------------------------------------------------------------------
# FSM Tests
# ---------------------------------------------------------------------------

class TestCmdNewScript:
    async def test_starts_dialog(self, mock_message, mock_state):
        await cmd_newscript(mock_message, mock_state)
        mock_state.set_state.assert_awaited_once_with(ScriptCreateFSM.name)
        mock_message.answer.assert_called_once()
        assert "название скрипта" in mock_message.answer.call_args[0][0].lower()


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
        mock_state.update_data.assert_awaited_with(tone="professional")
        mock_state.set_state.assert_awaited_with(ScriptCreateFSM.max_messages)

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
        assert "Проверьте данные" in mock_message.answer.call_args[0][0]


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
        mock_callback.answer.assert_awaited_once_with("✅ Скрипт создан!")


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

    async def test_rejects_non_document(self, mock_message, mock_state):
        mock_message.document = None
        await process_upload_file(mock_message, mock_state)
        mock_message.answer.assert_called_once_with("❌ Пожалуйста, отправьте файл.")

    async def test_rejects_unsupported_extension(self, mock_message, mock_state):
        mock_message.document = MagicMock()
        mock_message.document.file_name = "file.txt"
        await process_upload_file(mock_message, mock_state)
        mock_message.answer.assert_called_once_with("❌ Принимаются только CSV и Excel файлы.")


class TestCmdStartCampaign:
    async def test_no_draft_campaigns(self, mock_message, mock_state):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        context = _make_mock_session(result_mock)

        with patch("app.bots.admin_bot.AsyncSessionLocal", return_value=context):
            await cmd_startcampaign(mock_message, mock_state)

        mock_message.answer.assert_called_once_with("Нет кампаний со статусом draft.")

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
        assert "Выберите кампанию" in text


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

        mock_callback.answer.assert_awaited_once_with("❌ Кампания не найдена")
        mock_state.clear.assert_awaited_once()


class TestCampaignCreateFSM:
    async def test_select_script(self, mock_callback, mock_state):
        script_id = uuid.uuid4()
        mock_callback.data = f"campaign_script:{script_id}"
        await process_campaign_script(mock_callback, mock_state)
        mock_state.update_data.assert_awaited_with(script_id=script_id)
        mock_state.set_state.assert_awaited_with(CampaignCreateFSM.name)
