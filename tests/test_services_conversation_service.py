"""Tests for conversation service business logic."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.conversation import Conversation, Message
from app.services.conversation_service import (
    add_message,
    get_conversation_context,
    update_lead_facts,
)
from tests.conftest import MockResult, build_mock_session


@pytest.mark.asyncio
async def test_get_conversation_context_returns_messages_and_facts():
    conv_id = uuid.uuid4()
    msg1 = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        direction="outbound",
        content="Hello",
        sent_at=datetime(2024, 1, 1, 10, 0, 0),
    )
    msg2 = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        direction="inbound",
        content="Hi there",
        sent_at=datetime(2024, 1, 1, 10, 1, 0),
    )
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        facts_extracted={"budget": "10k"},
    )

    mock_db = build_mock_session()
    mock_db.execute.side_effect = [
        MockResult([msg2, msg1]),  # messages ordered desc
        MockResult([conversation]),  # conversation lookup
    ]

    result = await get_conversation_context(mock_db, conv_id, limit=10)

    assert result["messages"] == [msg1, msg2]  # reversed back to chronological
    assert result["facts"] == {"budget": "10k"}


@pytest.mark.asyncio
async def test_add_message_inserts_and_updates_timestamp():
    conv_id = uuid.uuid4()
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
    )

    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([conversation])
    mock_db.refresh = AsyncMock()

    message = await add_message(
        mock_db,
        conversation_id=conv_id,
        direction="outbound",
        content="Test message",
        message_type="text",
    )

    assert message.conversation_id == conv_id
    assert message.direction == "outbound"
    assert message.content == "Test message"
    assert conversation.last_message_at is not None
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(message)


@pytest.mark.asyncio
async def test_update_lead_facts_merges_jsonb():
    conv_id = uuid.uuid4()
    conversation = Conversation(
        id=conv_id,
        contact_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        facts_extracted={"budget": "10k"},
    )

    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([conversation])
    mock_db.refresh = AsyncMock()

    updated = await update_lead_facts(mock_db, conv_id, {"needs": "CRM", "budget": "15k"})

    assert updated.facts_extracted == {"budget": "15k", "needs": "CRM"}
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(conversation)


@pytest.mark.asyncio
async def test_update_lead_facts_raises_when_conversation_missing():
    conv_id = uuid.uuid4()
    mock_db = build_mock_session()
    mock_db.execute.return_value = MockResult([])

    with pytest.raises(ValueError, match=f"Conversation {conv_id} not found"):
        await update_lead_facts(mock_db, conv_id, {"needs": "CRM"})
