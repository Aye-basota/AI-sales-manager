"""Tests for inbound guardrails fallback behaviour."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bots.inbound_listener import _handle_inbound_message
from app.models.campaign import Campaign, CampaignContact
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.script import Script
from app.models.telegram_account import TelegramAccount
from tests.conftest import build_mock_session, MockResult


@pytest.mark.asyncio
async def test_guardrails_reject_fallback_sent():
    """When guardrails reject the LLM response, a fallback text is sent."""
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    client.set_online = AsyncMock()
    client.set_typing = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "What do you offer?"

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
        id=campaign.script_id,
        name="Test",
        role_prompt="Sales",
        goal="book a demo",
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
                # generate_response_with_guardrails returns fallback marker
                engine_inst.generate_response_with_guardrails = AsyncMock(
                    return_value={"text": "", "model": "fallback", "tokens_used": 0}
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
                            args, kwargs = client.send_message.call_args
                            assert "Извините, не совсем понял" in kwargs["text"]
                            assert "book a demo" in kwargs["text"]


@pytest.mark.asyncio
async def test_bot_check_uses_human_fallback_without_bot_words():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "Ты бот? Это автоматическая рассылка?"

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
        id=campaign.script_id,
        name="Test",
        role_prompt="Sales",
        goal="book a demo",
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
                    return_value={"text": "", "model": "fallback", "tokens_used": 0}
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
    engine_inst.generate_response_with_guardrails.assert_not_awaited()
    text = client.send_message.call_args.kwargs["text"].lower()
    assert "пишу из рабочего telegram" in text
    assert "бот" not in text
    assert "ии" not in text


@pytest.mark.asyncio
async def test_punctuation_only_inbound_uses_short_fallback_without_generation():
    account = TelegramAccount(id=uuid.uuid4(), phone="+123")
    client = MagicMock()
    client.set_online = AsyncMock()
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.read_history = AsyncMock()

    message = MagicMock()
    message.from_user = MagicMock(id=123456)
    message.text = "???"

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
        id=campaign.script_id,
        name="Test",
        role_prompt="Sales",
        goal="book a demo",
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
                engine_inst.generate_response_with_guardrails = AsyncMock()

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

    engine_inst.generate_response_with_guardrails.assert_not_awaited()
    client.send_message.assert_awaited_once()
    text = client.send_message.call_args.kwargs["text"]
    assert text.count("?") == 1
    assert "не в самый удобный момент" in text
