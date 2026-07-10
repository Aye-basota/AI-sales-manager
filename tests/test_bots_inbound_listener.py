import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bots.inbound_listener import (
    start_inbound_listeners,
    stop_inbound_listeners,
    _build_inbound_fallback_text,
    _handle_inbound_message,
    _needs_deterministic_fallback,
    _polish_inbound_response,
)
from app.models.telegram_account import TelegramAccount
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.campaign import Campaign, CampaignContact
from app.models.script import Script
from tests.conftest import build_mock_session, MockResult


class _FirstOnlyResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def scalar_one_or_none(self):
        raise AssertionError("handler should not use scalar_one_or_none for contacts")


@pytest.mark.asyncio
async def test_start_inbound_listeners_starts_clients():
    account = TelegramAccount(
        id=uuid.uuid4(),
        phone="+123",
        status="ready",
        session_string="sess",
    )
    mock_db = build_mock_session([account])

    with patch("app.bots.inbound_listener.SellerClient") as MockClient:
        client_inst = MockClient.return_value
        client_inst.start = AsyncMock()
        client_inst.on_message = MagicMock()
        client_inst._client = MagicMock()

        await start_inbound_listeners(mock_db)

        MockClient.assert_called_once()
        client_inst.start.assert_awaited_once()
        client_inst.on_message.assert_called_once()


@pytest.mark.asyncio
async def test_handle_inbound_message_tolerates_duplicate_contacts():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Не пишите мне"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    duplicate = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="Old")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="warm",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )
    script = Script(id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book")

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        _FirstOnlyResult([contact, duplicate]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.inbound_listener.asyncio.sleep", new_callable=AsyncMock):
            with patch(
                "app.bots.inbound_listener.extract_facts_from_message",
                new_callable=AsyncMock,
                return_value={},
            ):
                with patch(
                    "app.bots.inbound_listener.classify_intent",
                    new_callable=AsyncMock,
                    return_value="negative",
                ):
                    with patch(
                        "app.bots.inbound_listener.add_message",
                        new_callable=AsyncMock,
                    ):
                        await _handle_inbound_message(account, client, message)

    client.send_message.assert_awaited_once()
    assert "Больше не буду писать" in client.send_message.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_stop_inbound_listeners_stops_clients():
    mock_client = MagicMock()
    mock_client.stop = AsyncMock()
    with patch.dict(
        "app.bots.inbound_listener._inbound_clients", {"acc1": mock_client}, clear=True
    ):
        await stop_inbound_listeners()
    mock_client.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_inbound_message_existing_conversation():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.set_typing = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="positive",
        ):
            with patch("app.bots.inbound_listener.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={
                        "text": "Hi there",
                        "model": "gpt-4",
                        "tokens_used": 5,
                    }
                )

                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.get_conversation_context",
                        new_callable=AsyncMock,
                        return_value={"messages": [], "facts": {}},
                    ):
                        with patch(
                            "app.bots.inbound_listener.NotificationService.send_hot_lead_alert",
                            new_callable=AsyncMock,
                        ) as mock_notif:
                            with patch(
                                "app.bots.inbound_listener.add_message",
                                new_callable=AsyncMock,
                            ) as mock_add:
                                await _handle_inbound_message(account, client, message)

                                client.set_online.assert_awaited_once()
                                client.send_message.assert_awaited_once()
                                client.read_history.assert_awaited_once()
                                mock_add.assert_awaited()
                                mock_notif.assert_awaited_once()
                                assert conversation.current_state == "hot"
                                assert account.daily_messages_sent == 1
                                assert account.last_message_at is not None


@pytest.mark.asyncio
async def test_handle_inbound_message_new_conversation():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.set_typing = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    campaign = Campaign(id=uuid.uuid4(), script_id=uuid.uuid4(), status="running")
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="pending",
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([]),  # no conversation
        MockResult([cc]),
        MockResult([campaign]),
        MockResult([cc]),  # campaign contact for analytics update
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="negative",
        ):
            with patch("app.bots.inbound_listener.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={
                        "text": "Sure",
                        "model": "gpt-4",
                        "tokens_used": 3,
                    }
                )

                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.get_conversation_context",
                        new_callable=AsyncMock,
                        return_value={"messages": [], "facts": {}},
                    ):
                        with patch(
                            "app.bots.inbound_listener.NotificationService.send_hot_lead_alert",
                            new_callable=AsyncMock,
                        ) as mock_notif:
                            with patch(
                                "app.bots.inbound_listener.add_message",
                                new_callable=AsyncMock,
                            ) as mock_add:
                                await _handle_inbound_message(account, client, message)

                                client.send_message.assert_awaited_once()
                                sent_text = client.send_message.call_args.kwargs["text"]
                                assert "извините за беспокойство" in sent_text
                                assert "?" not in sent_text
                                mock_add.assert_awaited()
                                mock_notif.assert_not_awaited()
                                generate = engine_inst.generate_response_with_guardrails
                                generate.assert_not_awaited()
                                created_conversation = next(
                                    call.args[0]
                                    for call in mock_db.add.call_args_list
                                    if isinstance(call.args[0], Conversation)
                                )
                                assert created_conversation.current_state == "closed"
                                assert account.daily_messages_sent == 1


@pytest.mark.asyncio
async def test_handle_inbound_message_paused_campaign_does_not_update_analytics():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.send_message = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    campaign = Campaign(
        id=conversation.campaign_id,
        script_id=uuid.uuid4(),
        status="paused",
        replied_count=0,
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock):
            await _handle_inbound_message(account, client, message)

    # No automated reply sent because campaign is not running.
    client.send_message.assert_not_awaited()
    # Analytics must not be updated for paused campaigns.
    assert cc.status == "initial_sent"
    assert campaign.replied_count == 0


@pytest.mark.asyncio
async def test_handle_inbound_message_unknown_user():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    client.send_message = AsyncMock()
    message = MagicMock()
    message.from_user = MagicMock(id=999999)
    message.text = "Hello"

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([]),  # no contact
        MockResult([]),  # no conversation
        MockResult([]),  # no campaign contact
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_inbound_message(account, client, message)
        client.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbound_message_guardrails_block():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    client.set_online = AsyncMock()
    client.set_typing = AsyncMock()
    client.send_message = AsyncMock()
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="objection",
        ):
            with patch("app.bots.inbound_listener.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={
                        "text": "",
                        "model": "fallback",
                        "tokens_used": 0,
                    }
                )

                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.get_conversation_context",
                        new_callable=AsyncMock,
                        return_value={"messages": [], "facts": {}},
                    ):
                        with patch(
                            "app.bots.inbound_listener.NotificationService.send_hot_lead_alert",
                            new_callable=AsyncMock,
                        ) as mock_notif:
                            with patch(
                                "app.bots.inbound_listener.add_message",
                                new_callable=AsyncMock,
                            ):
                                await _handle_inbound_message(account, client, message)

                                # Fallback text should still be sent
                                client.send_message.assert_awaited_once()
                                args, kwargs = client.send_message.call_args
                                assert "Похоже, я не до конца точно понял вопрос" in kwargs["text"]
                                assert "Sales" in kwargs["text"]
                                assert "созвон" not in kwargs["text"].lower()
                                mock_notif.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbound_question_stays_warm_and_does_not_notify():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Сколько это стоит?"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="warm",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="question",
        ):
            with patch("app.bots.inbound_listener.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={
                        "text": "Стоимость зависит от объема. Какой у вас поток лидов?",
                        "model": "gpt-4",
                        "tokens_used": 3,
                    }
                )

                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.get_conversation_context",
                        new_callable=AsyncMock,
                        return_value={"messages": [], "facts": {}},
                    ):
                        with patch(
                            "app.bots.inbound_listener.NotificationService.send_hot_lead_alert",
                            new_callable=AsyncMock,
                        ) as mock_notif:
                            with patch(
                                "app.bots.inbound_listener.add_message",
                                new_callable=AsyncMock,
                            ):
                                await _handle_inbound_message(account, client, message)

    assert conversation.current_state == "warm"
    mock_notif.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbound_meeting_intent_confirms_and_stops():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Давайте созвонимся завтра после обеда"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="hot",
    )
    campaign = Campaign(
        id=conversation.campaign_id,
        script_id=uuid.uuid4(),
        status="running",
        meeting_booked_count=0,
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="meeting_intent",
        ):
            with patch("app.bots.inbound_listener.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock()

                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.NotificationService.send_hot_lead_alert",
                        new_callable=AsyncMock,
                    ) as mock_notif:
                        with patch(
                            "app.bots.inbound_listener.add_message",
                            new_callable=AsyncMock,
                        ):
                            await _handle_inbound_message(account, client, message)

    client.send_message.assert_awaited_once()
    sent_text = client.send_message.call_args.kwargs["text"]
    assert "договорились" in sent_text.lower()
    assert "?" not in sent_text
    assert conversation.current_state == "meeting_booked"
    assert cc.status == "meeting_booked"
    assert campaign.meeting_booked_count == 1
    engine_inst.generate_response_with_guardrails.assert_not_awaited()
    mock_notif.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_inbound_terminal_conversation_does_not_auto_reply():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Спасибо, до завтра"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="meeting_booked",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="meeting_booked",
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="informational",
        ):
            with patch("app.bots.inbound_listener.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock()

                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.NotificationService.send_hot_lead_alert",
                        new_callable=AsyncMock,
                    ) as mock_notif:
                        with patch(
                            "app.bots.inbound_listener.add_message",
                            new_callable=AsyncMock,
                        ):
                            await _handle_inbound_message(account, client, message)

    client.send_message.assert_not_awaited()
    assert conversation.current_state == "meeting_booked"
    engine_inst.generate_response_with_guardrails.assert_not_awaited()
    mock_notif.assert_not_awaited()


def test_polish_inbound_response_removes_robotic_pattern():
    text = (
        "Понимаю, а как сейчас решаете эту задачу?\n\n"
        "AI Sales Manager может показать пример.\n\n"
        "Кто у вас отвечает за это? Какой объем лидов?"
    )

    result = _polish_inbound_response(text)

    assert "как сейчас решаете эту задачу" not in result.lower()
    assert "AI Sales Manager" not in result
    assert "наш инструмент" in result
    assert result.count("?") <= 1
    assert result.count("\n\n") == 0


def test_deterministic_fallback_does_not_match_working_words():
    assert (
        _needs_deterministic_fallback(
            "Не уверен, у нас сейчас и так все вручную работает."
        )
        is False
    )
    assert _needs_deterministic_fallback("Ты бот? Это автоматическая рассылка?") is True


def test_fallback_text_does_not_match_bot_inside_working_words():
    script = Script(name="Test", goal="обсудить обработку лидов")
    text = _build_inbound_fallback_text(
        "Не уверен, у нас сейчас и так все вручную работает.",
        script,
    )

    assert "Пишу из рабочего Telegram" not in text
    assert "обсудить обработку лидов" in text
    assert "созвон" not in text.lower()


def test_short_positive_fallback_does_not_push_meeting():
    script = Script(
        name="Test",
        role_prompt="Помогаем B2B-командам аккуратно начинать диалоги в Telegram.",
        goal="объяснить механику",
    )
    text = _build_inbound_fallback_text("Ок, интересно", script)

    assert "Помогаем B2B-командам" in text
    assert "созвон" not in text.lower()
    assert "встреч" not in text.lower()


def test_short_positive_fallback_ignores_cta_goal_as_offer_context():
    script = Script(
        name="Test",
        role_prompt="Ты живой B2B sales manager. Не называй себя ботом.",
        goal="показать ценность AI Sales Manager и договориться о коротком созвоне",
        target_audience="B2B founders and sales managers",
    )
    text = _build_inbound_fallback_text("Да", script)

    assert "B2B-командам" in text
    assert "созвон" not in text.lower()
    assert "договориться" not in text.lower()


def test_polish_keeps_neural_lead_brand_name():
    result = _polish_inbound_response(
        "Я из Neural Lead. Написал по рабочему контакту."
    )

    assert "Neural Lead" in result
    assert "Neural лидом" not in result


def test_fallback_for_wrong_person_does_not_push_meeting():
    script = Script(name="Test", goal="договориться о созвоне")
    text = _build_inbound_fallback_text(
        "Это не ко мне, я не занимаюсь продажами.",
        script,
    )

    assert "не по адресу" in text
    assert "созвон" not in text.lower()
    assert "?" not in text
    assert _needs_deterministic_fallback("Это не ко мне") is True


def test_fallback_for_pause_does_not_continue_interrogation():
    script = Script(name="Test", goal="договориться о созвоне")
    text = _build_inbound_fallback_text(
        "Сейчас не до этого, напишите через пару месяцев.",
        script,
    )

    assert "не отвлекаю" in text
    assert "?" not in text


def test_pricing_patterns_match_natural_price_question():
    assert (
        _needs_deterministic_fallback(
            "Сколько это стоит? И чем вы лучше обычного менеджера?"
        )
        is True
    )


def test_pause_patterns_do_not_match_process_word_later():
    assert (
        _needs_deterministic_fallback(
            "У нас лиды из конференций, потом менеджер руками пишет в Telegram."
        )
        is False
    )


def test_integration_patterns_do_not_match_existing_crm_objection():
    assert (
        _needs_deterministic_fallback(
            "У нас уже есть CRM и менеджеры, зачем еще один инструмент?"
        )
        is False
    )


def test_fallback_for_integration_question_avoids_unsupported_claims():
    script = Script(name="Test", goal="договориться о созвоне")
    text = _build_inbound_fallback_text(
        "А с amoCRM или Bitrix24 это можно связать?",
        script,
    )

    assert "не буду обещать" in text
    assert "готовые коннекторы" not in text.lower()
    assert "работает" not in text.lower()


def test_polish_replaces_english_leads_word():
    text = _polish_inbound_response(
        "Расскажите, с какой задачей чаще всего тратите время на первые контакты с новыми leads?"
    )

    assert "leads" not in text.lower()
    assert "лидами" in text


def test_fallback_for_security_question_addresses_access_and_data():
    script = Script(name="Test", goal="договориться о созвоне")
    text = _build_inbound_fallback_text(
        "Что с безопасностью данных и доступами к Telegram аккаунту?",
        script,
    )

    assert "доступ" in text.lower()
    assert "данные" in text.lower()
    assert "не буду" in text.lower()


def test_fallback_for_case_question_avoids_fake_metrics():
    script = Script(name="Test", goal="договориться о созвоне")
    text = _build_inbound_fallback_text(
        "Есть кейсы по B2B SaaS или это пока только теория?",
        script,
    )

    assert "Не буду выдумывать кейсы" in text
    assert "+27%" not in text
    assert "3 раза" not in text
    assert "метрики обычно смотрят" not in text


def test_materials_request_does_not_promise_fake_attachments():
    script = Script(
        name="Стаканчики",
        role_prompt="Делаем кастомные бумажные стаканчики для кофеен.",
        goal="Обсудить регулярные поставки",
    )
    text = _build_inbound_fallback_text("Да, покажите примеры стаканчиков", script)

    lowered = text.lower()
    assert "не могу прикрепить" in lowered or "не буду выдумывать" in lowered
    assert "стаканчик" in lowered
    assert "лидогенерац" not in lowered
    assert "присылаю" not in lowered


def test_cups_pricing_fallback_stays_in_cups_context():
    script = Script(
        name="Стаканчики",
        role_prompt="Делаем кастомные бумажные стаканчики для кофеен.",
        goal="Обсудить регулярные поставки",
    )
    text = _build_inbound_fallback_text("Что за цифра, можете говорить конкретнее?", script)

    lowered = text.lower()
    assert "стакан" in lowered
    assert "тираж" in lowered
    assert "контактов" not in lowered


def test_context_confusion_fallback_resets_to_offer():
    script = Script(
        name="Стаканчики",
        role_prompt="Делаем кастомные бумажные стаканчики для кофеен.",
        goal="Обсудить регулярные поставки",
    )
    text = _build_inbound_fallback_text("Что ещё за сценарий? О чем вы?", script)

    lowered = text.lower()
    assert "сбился формулировкой" in lowered
    assert "стаканчик" in lowered
    assert "лидогенерац" not in lowered


def test_fallback_for_competitor_compare_is_not_bot_check():
    script = Script(name="Test", goal="договориться о созвоне")
    text = _build_inbound_fallback_text(
        "Чем вы отличаетесь от обычной рассылки через Telegram?",
        script,
    )

    assert "массовой отправке" in text
    assert "Пишу из рабочего Telegram" not in text


def test_fallback_for_english_request_is_short_and_safe():
    script = Script(name="Test", goal="договориться о созвоне")
    text = _build_inbound_fallback_text(
        "Can you explain in English what this does?",
        script,
    )

    assert "In short" in text
    assert "LinkedIn" not in text
    assert "email" not in text.lower()


@pytest.mark.asyncio
async def test_handle_inbound_message_skips_reply_when_daily_limit_reached():
    account = TelegramAccount(
        id=uuid.uuid4(), phone="+123", daily_messages_sent=50, last_message_at=None
    )
    client = MagicMock()
    client.send_message = AsyncMock()
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="positive",
        ):
            with patch(
                "app.bots.inbound_listener.extract_facts_from_message",
                new_callable=AsyncMock,
                return_value={},
            ):
                with patch(
                    "app.bots.inbound_listener.add_message",
                    new_callable=AsyncMock,
                ):
                    await _handle_inbound_message(account, client, message)

    client.send_message.assert_not_awaited()
    assert conversation.current_state == "hot"


@pytest.mark.asyncio
async def test_handle_inbound_message_replies_even_when_account_recently_sent():
    account = TelegramAccount(
        id=uuid.uuid4(),
        phone="+123",
        daily_messages_sent=0,
        last_message_at=datetime.now(timezone.utc),
    )
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )
    script = Script(
        id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book"
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([cc]),
        MockResult([script]),
        MockResult([account]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.bots.inbound_listener.classify_intent",
            new_callable=AsyncMock,
            return_value="positive",
        ):
            with patch("app.bots.inbound_listener.LLMEngine") as MockEngine:
                engine_inst = MockEngine.return_value
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={
                        "text": "Да, отвечу коротко: можем показать, где теряются лиды.",
                        "model": "gpt-4",
                        "tokens_used": 7,
                    }
                )
                with patch(
                    "app.bots.inbound_listener.extract_facts_from_message",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    with patch(
                        "app.bots.inbound_listener.get_conversation_context",
                        new_callable=AsyncMock,
                        return_value={"messages": [], "facts": {}},
                    ):
                        with patch(
                            "app.bots.inbound_listener.add_message",
                            new_callable=AsyncMock,
                        ):
                            await _handle_inbound_message(account, client, message)

    client.send_message.assert_awaited_once()
    assert account.daily_messages_sent == 1
    assert account.last_message_at is not None
    assert conversation.current_state == "hot"
