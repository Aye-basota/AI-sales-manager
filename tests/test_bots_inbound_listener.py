import asyncio
import importlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.bots.inbound_listener as inbound_listener_module
from app.bots.inbound_listener import (
    start_inbound_listeners,
    stop_inbound_listeners,
    _build_inbound_fallback_text,
    _dormant_reply_delay_seconds,
    _handle_inbound_message,
    _process_inbound_message,
    _needs_deterministic_fallback,
    _looks_like_hard_negative,
    _looks_like_offtopic_or_troll,
    _looks_like_technical_support_detour,
    _meeting_time_is_confirmed,
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
async def test_start_inbound_listeners_covers_unavailable_and_sessionless_accounts():
    account = TelegramAccount(
        id=uuid.uuid4(),
        phone="+123",
        status="ready",
        session_string=None,
    )
    mock_db = build_mock_session([account])

    with patch("app.bots.inbound_listener._PYROGRAM_AVAILABLE", False):
        await start_inbound_listeners(mock_db)

    with patch("app.bots.inbound_listener.SellerClient") as MockClient:
        await start_inbound_listeners(mock_db)

    MockClient.assert_not_called()


@pytest.mark.asyncio
async def test_start_inbound_listeners_uses_own_session_and_handles_client_failures():
    account_start_error = TelegramAccount(
        id=uuid.uuid4(),
        phone="+1",
        status="ready",
        session_string="sess1",
    )
    account_no_client = TelegramAccount(
        id=uuid.uuid4(),
        phone="+2",
        status="ready",
        session_string="sess2",
    )
    account_ok = TelegramAccount(
        id=uuid.uuid4(),
        phone="+3",
        status="ready",
        session_string="sess3",
    )
    mock_db = build_mock_session([account_start_error, account_no_client, account_ok])

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        clients = []

        def client_factory(*args, **kwargs):
            client = MagicMock()
            client.start = AsyncMock()
            client.on_message = MagicMock()
            client._client = MagicMock()
            clients.append(client)
            return client

        with patch("app.bots.inbound_listener.SellerClient", side_effect=client_factory):
            with patch(
                "app.bots.inbound_listener._handle_inbound_message",
                new_callable=AsyncMock,
            ) as mock_handle:
                clients_created = []

                def collect_client(*args, **kwargs):
                    client = client_factory(*args, **kwargs)
                    clients_created.append(client)
                    return client

                with patch(
                    "app.bots.inbound_listener.SellerClient",
                    side_effect=collect_client,
                ):
                    clients_created_side_effects = [
                        RuntimeError("start failed"),
                        None,
                        None,
                    ]

                    async def start_side_effect_factory(client, index):
                        if clients_created_side_effects[index] is not None:
                            raise clients_created_side_effects[index]

                    # Rebuild clients with per-client start behavior.
                    def client_factory_with_behaviour(*args, **kwargs):
                        index = len(clients_created)
                        client = MagicMock()
                        client.start = AsyncMock(
                            side_effect=(
                                RuntimeError("start failed") if index == 0 else None
                            )
                        )
                        client.on_message = MagicMock()
                        client._client = None if index == 1 else MagicMock()
                        clients_created.append(client)
                        return client

                    with patch(
                        "app.bots.inbound_listener.SellerClient",
                        side_effect=client_factory_with_behaviour,
                    ):
                        await start_inbound_listeners()

                ok_client = clients_created[2]
                handler = ok_client.on_message.call_args.args[0]
                message = MagicMock()
                await handler(None, message)

    mock_handle.assert_awaited_once_with(account_ok, ok_client, message)


@pytest.mark.asyncio
async def test_stop_inbound_listeners_logs_stop_errors():
    mock_client = MagicMock()
    mock_client.stop = AsyncMock(side_effect=RuntimeError("stop failed"))
    with patch.dict(
        "app.bots.inbound_listener._inbound_clients", {"acc1": mock_client}, clear=True
    ):
        await stop_inbound_listeners()

    mock_client.stop.assert_awaited_once()


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
    assert "больше не буду писать" in client.send_message.call_args.kwargs["text"].lower()
    assert cc.status == "closed"


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
async def test_handle_inbound_batches_quick_messages():
    account = MagicMock(id=uuid.uuid4())
    client = MagicMock()
    msg1 = MagicMock()
    msg1.from_user = MagicMock(id=123456)
    msg1.text = "Да, интересно"
    msg2 = MagicMock()
    msg2.from_user = MagicMock(id=123456)
    msg2.text = "И скажите по срокам"

    processed: list[str | None] = []

    async def fake_process(*args, combined_text=None, **kwargs):
        processed.append(combined_text)

    with (
        patch("app.bots.inbound_listener.INBOUND_BATCH_DELAY_SECONDS", 0.02),
        patch(
            "app.bots.inbound_listener._process_inbound_message",
            new=AsyncMock(side_effect=fake_process),
        ) as process_mock,
    ):
        await asyncio.gather(
            _handle_inbound_message(account, client, msg1),
            _handle_inbound_message(account, client, msg2),
        )

    assert process_mock.await_count == 1
    assert processed == ["Да, интересно\nИ скажите по срокам"]


@pytest.mark.asyncio
async def test_handle_inbound_extends_batch_until_quiet_window():
    account = MagicMock(id=uuid.uuid4())
    client = MagicMock()
    msg1 = MagicMock()
    msg1.from_user = MagicMock(id=123456)
    msg1.text = "Да, могу в пятницу"
    msg2 = MagicMock()
    msg2.from_user = MagicMock(id=123456)
    msg2.text = "после 15:00"

    processed: list[str | None] = []

    async def fake_process(*args, combined_text=None, **kwargs):
        processed.append(combined_text)

    with (
        patch("app.bots.inbound_listener.INBOUND_BATCH_DELAY_SECONDS", 0.02),
        patch(
            "app.bots.inbound_listener._process_inbound_message",
            new=AsyncMock(side_effect=fake_process),
        ) as process_mock,
    ):
        first = asyncio.create_task(_handle_inbound_message(account, client, msg1))
        await asyncio.sleep(0.01)
        second = asyncio.create_task(_handle_inbound_message(account, client, msg2))
        await asyncio.gather(first, second)

    assert process_mock.await_count == 1
    assert processed == ["Да, могу в пятницу\nпосле 15:00"]


@pytest.mark.asyncio
async def test_handle_inbound_message_early_returns_and_empty_batch():
    account = MagicMock(id=uuid.uuid4())
    client = MagicMock()

    no_user = MagicMock(from_user=None, text="Hello")
    await _handle_inbound_message(account, client, no_user)

    no_text = MagicMock()
    no_text.from_user = MagicMock(id=123456)
    no_text.text = ""
    await _handle_inbound_message(account, client, no_text)

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"
    key = (str(account.id), 123456)

    async def clear_batch(_delay):
        inbound_listener_module._pending_inbound_batches[key] = []

    with (
        patch("app.bots.inbound_listener.INBOUND_BATCH_DELAY_SECONDS", 0),
        patch(
            "app.bots.inbound_listener.asyncio.sleep",
            new=AsyncMock(side_effect=clear_batch),
        ),
        patch(
            "app.bots.inbound_listener._process_inbound_message",
            new_callable=AsyncMock,
        ) as mock_process,
    ):
        await _handle_inbound_message(account, client, message)

    mock_process.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_inbound_message_early_returns_without_user_or_text():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()

    await _process_inbound_message(account, client, MagicMock(from_user=None))

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = ""
    await _process_inbound_message(account, client, message)


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
                                assert "извините за беспокойство" in sent_text.lower()
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
                                assert cc.status == "closed"
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
        MockResult([cc]),
    ]

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock):
            await _handle_inbound_message(account, client, message)

    # No automated reply sent because campaign is not running.
    client.send_message.assert_not_awaited()
    # Status is updated so the scheduler will not later send a stale follow-up,
    # but analytics must not be updated for paused campaigns.
    assert cc.status == "replied"
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
async def test_process_inbound_creates_contact_but_skips_without_campaign_membership():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    message = MagicMock()
    message.from_user = MagicMock(
        id=777,
        username="newlead",
        first_name="New",
        last_name="Lead",
    )
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

        await _process_inbound_message(account, client, message)

    created_contact = mock_db.add.call_args.args[0]
    assert isinstance(created_contact, Contact)
    assert created_contact.telegram_username == "newlead"


@pytest.mark.asyncio
async def test_process_inbound_skips_when_campaign_missing_or_conversation_has_no_campaign():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"
    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456)
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        contact_id=contact.id,
        status="initial_sent",
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([]),
        MockResult([cc]),
        MockResult([]),  # no campaign for campaign contact
    ]
    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        await _process_inbound_message(account, client, message)

    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([]),  # no campaign for existing conversation
    ]
    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock) as mock_add:
            await _process_inbound_message(account, client, message)

    mock_add.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_inbound_updates_facts_and_skips_when_script_missing():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.read_history = AsyncMock()
    client.send_message = AsyncMock()
    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Мы кофейня"
    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456)
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    campaign = Campaign(
        id=conversation.campaign_id,
        script_id=uuid.uuid4(),
        status="running",
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
        MockResult([cc]),
        MockResult([]),  # no script
    ]
    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        with (
            patch("app.bots.inbound_listener.asyncio.sleep", new_callable=AsyncMock),
            patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
            patch(
                "app.bots.inbound_listener.extract_facts_from_message",
                new_callable=AsyncMock,
                return_value={"business": "coffee"},
            ),
            patch(
                "app.bots.inbound_listener.update_lead_facts",
                new_callable=AsyncMock,
            ) as mock_update_facts,
        ):
            await _process_inbound_message(account, client, message)

    mock_update_facts.assert_awaited_once_with(
        mock_db, conversation.id, {"business": "coffee"}
    )
    client.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_inbound_fact_extraction_failure_is_non_fatal():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.read_history = AsyncMock()
    client.send_message = AsyncMock()
    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Мы кофейня"
    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456)
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
    )
    campaign = Campaign(
        id=conversation.campaign_id,
        script_id=uuid.uuid4(),
        status="running",
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
        MockResult([cc]),
        MockResult([]),  # no script: stop after fact extraction branch
    ]
    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        with (
            patch("app.bots.inbound_listener.asyncio.sleep", new_callable=AsyncMock),
            patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
            patch(
                "app.bots.inbound_listener.extract_facts_from_message",
                new_callable=AsyncMock,
                side_effect=RuntimeError("facts down"),
            ),
            patch("app.bots.inbound_listener.logger.debug") as mock_debug,
        ):
            await _process_inbound_message(account, client, message)

    mock_debug.assert_called()
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
                                assert "Sales" not in kwargs["text"]
                                assert "без лишней ручной рутины" in kwargs["text"]
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


def test_meeting_time_confirmation_requires_concrete_accepted_slot():
    assert _meeting_time_is_confirmed("Да, завтра в 11:00 подходит") is True
    assert _meeting_time_is_confirmed("Давайте созвонимся завтра после обеда") is False
    assert _meeting_time_is_confirmed("завтра до 18.00 нет возможности?") is False


@pytest.mark.asyncio
async def test_handle_inbound_confirmed_meeting_time_confirms_and_stops():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Да, завтра в 11:00 подходит"

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
async def test_handle_inbound_broad_meeting_intent_keeps_dialog_open():
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
    script = Script(id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book")
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
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={"text": "Давайте сверю окно и вернусь по времени.", "model": "gpt", "tokens_used": 1}
                )

                with (
                    patch("app.bots.inbound_listener.extract_facts_from_message", new_callable=AsyncMock, return_value={}),
                    patch("app.bots.inbound_listener.get_conversation_context", new_callable=AsyncMock, return_value={"messages": [], "facts": {}}),
                    patch("app.bots.inbound_listener.NotificationService.send_hot_lead_alert", new_callable=AsyncMock) as mock_notif,
                    patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
                ):
                    await _handle_inbound_message(account, client, message)

    assert conversation.current_state == "hot"
    assert conversation.conversation_stage == "cta"
    assert cc.status == "replied"
    assert campaign.meeting_booked_count == 0
    sent_text = client.send_message.call_args.kwargs["text"]
    assert "не хочу обещать слот наугад" in sent_text.lower()
    engine_inst.generate_response_with_guardrails.assert_not_awaited()
    mock_notif.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbound_terminal_conversation_does_not_auto_reply():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Спасибо"

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


@pytest.mark.asyncio
async def test_closed_conversation_reopens_when_lead_returns_with_interest():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Я передумал, расскажите подробнее"

    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="closed",
        conversation_stage="interest",
    )
    campaign = Campaign(
        id=conversation.campaign_id,
        script_id=uuid.uuid4(),
        status="running",
        replied_count=1,
    )
    script = Script(id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book")
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="closed",
        reply_received_at=datetime.now(timezone.utc),
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

        with (
            patch("app.bots.inbound_listener.classify_intent", new_callable=AsyncMock, return_value="question"),
            patch("app.bots.inbound_listener.LLMEngine") as MockEngine,
            patch("app.bots.inbound_listener.extract_facts_from_message", new_callable=AsyncMock, return_value={}),
            patch("app.bots.inbound_listener.get_conversation_context", new_callable=AsyncMock, return_value={"messages": [], "facts": {}}),
            patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
            patch("app.bots.inbound_listener.calculate_thinking_delay", return_value=0),
            patch("app.bots.inbound_listener.calculate_typing_delay", return_value=100),
        ):
            engine_inst = MockEngine.return_value
            engine_inst.generate_response_with_guardrails = AsyncMock(
                return_value={
                    "text": "Конечно, расскажу подробнее.",
                    "model": "gpt",
                    "tokens_used": 1,
                }
            )

            await _handle_inbound_message(account, client, message)

    client.send_message.assert_awaited_once()
    engine_inst.generate_response_with_guardrails.assert_awaited_once()
    assert conversation.current_state == "warm"
    assert cc.status == "replied"
    assert campaign.replied_count == 1


@pytest.mark.asyncio
async def test_meeting_booked_scheduling_question_gets_safe_reply():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "занято уже чтоли всё?"

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
    script = Script(id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book")
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

        with (
            patch("app.bots.inbound_listener.classify_intent", new_callable=AsyncMock, return_value="question"),
            patch("app.bots.inbound_listener.LLMEngine") as MockEngine,
            patch("app.bots.inbound_listener.extract_facts_from_message", new_callable=AsyncMock, return_value={}),
            patch("app.bots.inbound_listener.get_conversation_context", new_callable=AsyncMock, return_value={"messages": [], "facts": {}}),
            patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock()
            await _handle_inbound_message(account, client, message)

    client.send_message.assert_awaited_once()
    sent_text = client.send_message.call_args.kwargs["text"]
    assert "не хочу обещать слот наугад" in sent_text.lower()
    MockEngine.return_value.generate_response_with_guardrails.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbound_offtopic_is_negative_without_llm_classification():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()
    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Напиши пузырьковую сортировку на Python"

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
    script = Script(id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book")
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
        with (
            patch("app.bots.inbound_listener.asyncio.sleep", new_callable=AsyncMock),
            patch("app.bots.inbound_listener.extract_facts_from_message", new_callable=AsyncMock, return_value={}),
            patch("app.bots.inbound_listener.classify_intent", new_callable=AsyncMock) as mock_classify,
            patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
        ):
            await _process_inbound_message(account, client, message)

    mock_classify.assert_not_awaited()
    assert cc.status == "closed"
    assert conversation.current_state == "closed"
    client.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_inbound_uses_last_agent_context_and_waits_between_chunks():
    from app.models.conversation import Message

    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()
    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Расскажите подробнее"
    contact = Contact(id=uuid.uuid4(), telegram_user_id=123456, first_name="John")
    conversation = Conversation(
        id=uuid.uuid4(),
        contact_id=contact.id,
        campaign_id=uuid.uuid4(),
        current_state="cold",
        conversation_stage="trust",
    )
    campaign = Campaign(
        id=conversation.campaign_id, script_id=uuid.uuid4(), status="running"
    )
    script = Script(id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book")
    cc = CampaignContact(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        status="initial_sent",
    )
    history = [
        Message(direction="inbound", content="Привет"),
        Message(direction="outbound", content="Последний ответ"),
    ]

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
        with (
            patch("app.bots.inbound_listener.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("app.bots.inbound_listener.classify_intent", new_callable=AsyncMock, return_value="informational"),
            patch("app.bots.inbound_listener.extract_facts_from_message", new_callable=AsyncMock, return_value={}),
            patch("app.bots.inbound_listener.get_conversation_context", new_callable=AsyncMock, return_value={"messages": history, "facts": {}}),
            patch("app.bots.inbound_listener.build_reply_user_prompt", return_value="prompt") as mock_prompt,
            patch("app.bots.inbound_listener.LLMEngine") as MockEngine,
            patch("app.bots.inbound_listener.split_message_into_chunks", return_value=["one", "two"]),
            patch("app.bots.inbound_listener.calculate_thinking_delay", return_value=0),
            patch("app.bots.inbound_listener.calculate_typing_delay", return_value=100),
            patch("app.core.humanizer.chunk_pause_seconds", return_value=0.01),
            patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                return_value={"text": "one two", "model": "gpt", "tokens_used": 1}
            )
            await _process_inbound_message(account, client, message)

    assert mock_prompt.call_args.kwargs["last_agent_message"] == "Последний ответ"
    assert client.send_message.await_count == 2
    mock_sleep.assert_any_await(0.01)


@pytest.mark.asyncio
async def test_handle_inbound_llm_exception_falls_back_to_safe_text():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123", daily_messages_sent=0)
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()
    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Что это?"
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
    script = Script(id=campaign.script_id, name="Test", role_prompt="Sales", goal="Book")
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
        with (
            patch("app.bots.inbound_listener.asyncio.sleep", new_callable=AsyncMock),
            patch("app.bots.inbound_listener.classify_intent", new_callable=AsyncMock, return_value="informational"),
            patch("app.bots.inbound_listener.extract_facts_from_message", new_callable=AsyncMock, return_value={}),
            patch("app.bots.inbound_listener.get_conversation_context", new_callable=AsyncMock, return_value={"messages": [], "facts": {}}),
            patch("app.bots.inbound_listener.LLMEngine") as MockEngine,
            patch("app.bots.inbound_listener.add_message", new_callable=AsyncMock),
        ):
            MockEngine.return_value.generate_response_with_guardrails = AsyncMock(
                side_effect=RuntimeError("llm down")
            )
            await _process_inbound_message(account, client, message)

    sent_text = client.send_message.call_args.kwargs["text"]
    assert "Похоже, я не до конца точно понял вопрос" in sent_text


@pytest.mark.asyncio
async def test_handle_inbound_outer_exception_is_logged():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"
    mock_db = build_mock_session()
    mock_db.execute.side_effect = RuntimeError("db down")

    with patch("app.bots.inbound_listener.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch("app.bots.inbound_listener.logger.exception") as mock_exception:
            await _process_inbound_message(account, client, message)

    mock_exception.assert_called_once()


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


def test_script_offer_context_defaults_truncates_and_ignores_instruction_prompt():
    assert (
        inbound_listener_module._script_offer_context(None)
        == "помогаем решить эту задачу аккуратно и без лишней ручной рутины"
    )
    long_goal = "Описание " * 40
    script = Script(name="Long", role_prompt="", goal=long_goal, target_audience="")
    assert (
        inbound_listener_module._script_offer_context(script)
        == "помогаем решить эту задачу аккуратно и без лишней ручной рутины"
    )

    instruction_script = Script(
        name="Instruction",
        role_prompt="Ты sales manager. Не называй себя ботом.",
        goal="",
        target_audience="B2B founders and sales managers",
    )
    assert (
        inbound_listener_module._script_offer_context(instruction_script)
        == "помогаем решить эту задачу аккуратно и без лишней ручной рутины"
    )

    massage_script = Script(
        name="Элитный массаж",
        role_prompt=(
            "Предоставляем услуги массажа. У нас самые лучшие массажистки Москвы. "
            "Бархатные нежные ласковые."
        ),
        goal="",
        target_audience="",
    )
    assert inbound_listener_module._script_offer_context(massage_script) == "услуги массажа"


def test_polish_inbound_response_empty_and_multiple_questions():
    assert _polish_inbound_response("  ") == ""
    result = _polish_inbound_response("Первый вопрос? Второй вопрос? Утверждение.")
    assert result == "Первый вопрос?"


def test_polish_inbound_response_skips_empty_split_sentences():
    with patch(
        "app.bots.inbound_listener.re.split",
        side_effect=[["Первый? Второй?"], ["", "Первый?", "Второй?"]],
    ):
        assert _polish_inbound_response("Первый? Второй?") == "Первый?"


def test_delivery_contact_source_and_materials_fallbacks_are_safe():
    script = Script(
        name="Test",
        role_prompt="Помогаем B2B-командам аккуратно начинать диалоги.",
        goal="",
    )

    delivery = _build_inbound_fallback_text("Telegram заблокирует за спам?", script)
    assert "не предлагаем массово слать" in delivery

    source = _build_inbound_fallback_text("Кто вы и откуда взяли контакт?", script)
    assert "открытого контекста" in source

    materials = _build_inbound_fallback_text("Пришлите каталог и презентацию", script)
    assert "не могу прикрепить" in materials


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
    assert "обсудить обработку лидов" not in text
    assert "без лишней ручной рутины" in text
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

    assert "без лишней ручной рутины" in text
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


def test_generic_pricing_fallback_is_soft_and_does_not_repeat_robotic_phrase():
    script = Script(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа.",
        goal="Пригласить в салон",
    )

    text = _build_inbound_fallback_text("А цену то скажи за базовые услуги", script)
    lowered = text.lower()

    assert "по цене честно" in lowered
    assert "актуального прайса" in lowered
    assert "встреч" in lowered
    assert "ради цены" in lowered
    assert "точной вилки в текущем контексте" not in lowered


def test_price_handoff_question_does_not_schedule_meeting():
    script = Script(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа.",
        goal="Пригласить в салон",
    )

    text = _build_inbound_fallback_text("А с кем мне его сверить?", script)
    lowered = text.lower()

    assert "не встреча нужна" in lowered
    assert "актуальный прайс" in lowered
    assert "не буду придумывать" in lowered
    assert "удобное время" not in lowered


def test_meeting_confusion_repairs_previous_bad_cta():
    script = Script(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа.",
        goal="Пригласить в салон",
    )

    text = _build_inbound_fallback_text(
        "Просто встреча с менеджером это странно чтобы узнать цену услуги",
        script,
    )
    lowered = text.lower()

    assert "согласен" in lowered
    assert "встреча не нужна" in lowered
    assert "узнать цену" in lowered
    assert "точную сумму" in lowered


def test_suspicion_fallback_answers_without_pushy_cta():
    script = Script(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа.",
        goal="Пригласить в салон",
    )

    text = _build_inbound_fallback_text("А что вы предлагаете, звучит подозрительно", script)
    lowered = text.lower()

    assert "выглядеть подозрительно" in lowered
    assert "услуги массажа" in lowered
    assert "условия" in lowered
    assert "встреч" not in lowered


def test_offtopic_troll_detection_matches_bubble_sort_request():
    assert _looks_like_offtopic_or_troll("Напиши пузырьковую сортировку на Python")


def test_technical_support_detour_is_not_terminal_troll():
    text = "FATAL remaining connection slots, SQL запросы возвращают 500"

    assert _looks_like_technical_support_detour(text) is True
    assert _needs_deterministic_fallback(text) is True


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
    text = _build_inbound_fallback_text("Пришлите фото примеров стаканчиков", script)

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
    assert "я про" in lowered
    assert "стаканчик" in lowered
    assert "лидогенерац" not in lowered


def test_scheduling_fallback_uses_recent_window_from_history():
    script = Script(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа.",
        goal="Пригласить в салон",
    )
    history = [
        {"role": "agent", "content": "Мы на Университетской, корпус 1."},
        {"role": "lead", "content": "Да, могу в пятницу после 15:00."},
    ]

    text = _build_inbound_fallback_text(
        "Так когда и во сколько мне подойти?",
        script,
        history=history,
    )
    lowered = text.lower()

    assert "пятницу после 15:00" in lowered
    assert "предварительным окном" in lowered
    assert "обещать наугад" in lowered


def test_technical_troll_fallback_stays_in_role():
    script = Script(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа. У нас самые лучшие массажистки Москвы.",
        goal="Пригласить в салон",
    )
    text = _build_inbound_fallback_text(
        'FATAL: remaining connection slots are reserved. Сервис падает, 500, куда копать?',
        script,
    )
    lowered = text.lower()

    assert "техподдерж" in lowered
    assert "продакшн" in lowered
    assert "массажист" not in lowered
    assert "бархат" not in lowered


def test_hesitation_and_reconsideration_fallbacks_are_human():
    script = Script(
        name="Элитный массаж",
        role_prompt="Предоставляем услуги массажа.",
        goal="Пригласить в салон",
    )

    hesitation = _build_inbound_fallback_text("Даже не знаю", script).lower()
    assert "не буду уговаривать" in hesitation
    assert "мастериц" not in hesitation

    reconsider = _build_inbound_fallback_text(
        "Хотя я так подумал, впринципе можно",
        script,
    ).lower()
    assert "без спешки" in reconsider
    assert "свяжусь с мастером" not in reconsider


def test_hard_negative_visit_cancel_is_terminal_without_contradiction():
    assert _looks_like_hard_negative("Я не прийду") is True
    text = inbound_listener_module._terminal_response("negative", "Я не прийду")
    lowered = text.lower()

    assert "не закладываю" in lowered
    assert "жд" not in lowered


def test_dormant_reply_delay_tiers():
    now = datetime(2026, 7, 12, 17, 0, tzinfo=timezone.utc)

    assert _dormant_reply_delay_seconds(None, now=now) == 0
    assert (
        _dormant_reply_delay_seconds(
            datetime(2026, 7, 12, 16, 50, tzinfo=timezone.utc),
            now=now,
        )
        == 0
    )
    assert (
        _dormant_reply_delay_seconds(
            datetime(2026, 7, 12, 16, 0, tzinfo=timezone.utc),
            now=now,
        )
        == inbound_listener_module.DORMANT_REPLY_MEDIUM_DELAY_SECONDS
    )
    assert (
        _dormant_reply_delay_seconds(
            datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
            now=now,
        )
        == inbound_listener_module.DORMANT_REPLY_LONG_DELAY_SECONDS
    )


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


def test_inbound_listener_import_sets_event_loop_when_missing():
    loop = asyncio.new_event_loop()
    try:
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            with patch("asyncio.new_event_loop", return_value=loop) as mock_new_loop:
                with patch("asyncio.set_event_loop") as mock_set_loop:
                    importlib.reload(inbound_listener_module)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(loop)
    finally:
        importlib.reload(inbound_listener_module)
        loop.close()
