import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bots.inbound_listener import (
    start_inbound_listeners,
    stop_inbound_listeners,
    _handle_inbound_message,
)
from app.models.telegram_account import TelegramAccount
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.campaign import Campaign, CampaignContact
from app.models.script import Script
from tests.conftest import build_mock_session, MockResult


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
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    client.set_online = AsyncMock()
    client.set_typing = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(
        id=uuid.uuid4(), telegram_user_id=123456, first_name="John"
    )
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

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([script]),
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
                                await _handle_inbound_message(
                                    account, client, message
                                )

                                client.set_online.assert_awaited_once()
                                client.set_typing.assert_awaited_once()
                                client.send_message.assert_awaited_once()
                                client.read_history.assert_awaited_once()
                                mock_add.assert_awaited()
                                mock_notif.assert_awaited_once()
                                assert conversation.current_state == "hot"


@pytest.mark.asyncio
async def test_handle_inbound_message_new_conversation():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    client.set_online = AsyncMock()
    client.set_typing = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Hello"

    contact = Contact(
        id=uuid.uuid4(), telegram_user_id=123456, first_name="John"
    )
    campaign = Campaign(
        id=uuid.uuid4(), script_id=uuid.uuid4(), status="running"
    )
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
        MockResult([script]),
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
                                await _handle_inbound_message(
                                    account, client, message
                                )

                                client.send_message.assert_awaited_once()
                                mock_add.assert_awaited()
                                mock_notif.assert_not_awaited()


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

    contact = Contact(
        id=uuid.uuid4(), telegram_user_id=123456, first_name="John"
    )
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

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([contact]),
        MockResult([conversation]),
        MockResult([campaign]),
        MockResult([script]),
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
                                await _handle_inbound_message(
                                    account, client, message
                                )

                                # Fallback text should still be sent
                                client.send_message.assert_awaited_once()
                                args, kwargs = client.send_message.call_args
                                assert "Извините, не совсем понял" in kwargs["text"]
                                mock_notif.assert_not_awaited()
